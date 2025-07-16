import pandas as pd
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from collections import defaultdict

class OutletClustering:
    def __init__(self, radius_km=8, min_outlets_per_cluster=2, max_merge_distance_km=20):
        self.radius_km = radius_km
        self.min_outlets_per_cluster = min_outlets_per_cluster
        self.max_merge_distance_km = max_merge_distance_km
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        r = 6371
        return c * r
    
    def create_distance_matrix(self, coords):
        n = len(coords)
        dist_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                lat1, lon1 = coords[i]
                lat2, lon2 = coords[j]
                dist = self.haversine_distance(lat1, lon1, lat2, lon2)
                dist_matrix[i, j] = dist
                dist_matrix[j, i] = dist
        
        return dist_matrix
    
    def group_outlets_by_radius(self, df, max_iterations=20):
        df_valid = df[(df['latitude'] != 0) & (df['longitude'] != 0)].copy()
        
        coords = df_valid[['latitude', 'longitude']].values
        
        initial_threshold = self.radius_km * 0.5
        
        distance_matrix = self.create_distance_matrix(coords)
        
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=initial_threshold,
            metric='precomputed',
            linkage='single'
        ).fit(distance_matrix)
        
        df_valid['cluster'] = clustering.labels_
        
        for iteration in range(max_iterations):
            cluster_centers = defaultdict(list)
            for idx, row in df_valid.iterrows():
                cluster_centers[row['cluster']].append((row['latitude'], row['longitude']))
            
            for cluster in cluster_centers:
                lats = [coord[0] for coord in cluster_centers[cluster]]
                lons = [coord[1] for coord in cluster_centers[cluster]]
                cluster_centers[cluster] = (np.mean(lats), np.mean(lons))
            
            df_valid['center_lat'] = df_valid['cluster'].map(lambda x: cluster_centers[x][0])
            df_valid['center_lon'] = df_valid['cluster'].map(lambda x: cluster_centers[x][1])
            
            df_valid['distance_to_center_km'] = df_valid.apply(
                lambda row: self.haversine_distance(
                    row['latitude'], row['longitude'],
                    row['center_lat'], row['center_lon']
                ), 
                axis=1
            )
            
            outliers = df_valid[df_valid['distance_to_center_km'] > self.radius_km].copy()
            
            if len(outliers) == 0:
                break
            
            next_cluster_id = df_valid['cluster'].max() + 1
            for idx, row in outliers.iterrows():
                df_valid.loc[idx, 'cluster'] = next_cluster_id
                next_cluster_id += 1
        
        while True:
            cluster_centers = defaultdict(list)
            for idx, row in df_valid.iterrows():
                cluster_centers[row['cluster']].append((row['latitude'], row['longitude']))
            
            for cluster in cluster_centers:
                lats = [coord[0] for coord in cluster_centers[cluster]]
                lons = [coord[1] for coord in cluster_centers[cluster]]
                cluster_centers[cluster] = (np.mean(lats), np.mean(lons))
            
            df_valid['center_lat'] = df_valid['cluster'].map(lambda x: cluster_centers[x][0])
            df_valid['center_lon'] = df_valid['cluster'].map(lambda x: cluster_centers[x][1])
            
            df_valid['distance_to_center_km'] = df_valid.apply(
                lambda row: self.haversine_distance(
                    row['latitude'], row['longitude'],
                    row['center_lat'], row['center_lon']
                ), 
                axis=1
            )
            
            outliers = df_valid[df_valid['distance_to_center_km'] > self.radius_km].copy()
            
            if len(outliers) == 0:
                break
                
            next_cluster_id = df_valid['cluster'].max() + 1
            for idx, row in outliers.iterrows():
                df_valid.loc[idx, 'cluster'] = next_cluster_id
                next_cluster_id += 1
        
        df_invalid = df[(df['latitude'] == 0) | (df['longitude'] == 0)].copy()
        if not df_invalid.empty:
            max_cluster = df_valid['cluster'].max() + 1
            df_invalid['cluster'] = range(max_cluster, max_cluster + len(df_invalid))
            df_invalid['center_lat'] = 0
            df_invalid['center_lon'] = 0
            df_invalid['distance_to_center_km'] = 0
            
        result = pd.concat([df_valid, df_invalid])
        
        cluster_centers = defaultdict(list)
        for idx, row in result.iterrows():
            if row['latitude'] != 0 and row['longitude'] != 0:
                cluster_centers[row['cluster']].append((row['latitude'], row['longitude']))
        
        for cluster in cluster_centers:
            lats = [coord[0] for coord in cluster_centers[cluster]]
            lons = [coord[1] for coord in cluster_centers[cluster]]
            cluster_centers[cluster] = (np.mean(lats), np.mean(lons))
        
        result['center_lat'] = result['cluster'].map(lambda x: cluster_centers.get(x, (0, 0))[0])
        result['center_lon'] = result['cluster'].map(lambda x: cluster_centers.get(x, (0, 0))[1])
        
        result['distance_to_center_km'] = result.apply(
            lambda row: self.haversine_distance(
                row['latitude'], row['longitude'],
                row['center_lat'], row['center_lon']
            ) if row['latitude'] != 0 and row['longitude'] != 0 else 0, 
            axis=1
        )
        
        changes_made = True
        merge_iteration = 0
        max_merge_iterations = 20
        
        while changes_made and merge_iteration < max_merge_iterations:
            changes_made = False
            merge_iteration += 1
            
            cluster_counts = result['cluster'].value_counts()
            single_outlet_clusters = cluster_counts[cluster_counts < self.min_outlets_per_cluster].index.tolist()
            
            if not single_outlet_clusters:
                break
                
            for single_cluster in single_outlet_clusters:
                single_outlets = result[result['cluster'] == single_cluster]
                
                for idx, outlet in single_outlets.iterrows():
                    if outlet['latitude'] == 0 or outlet['longitude'] == 0:
                        continue
                        
                    nearest_cluster = None
                    min_distance = float('inf')
                    
                    for other_cluster in cluster_centers:
                        if other_cluster == single_cluster or other_cluster in single_outlet_clusters:
                            continue
                            
                        center_lat, center_lon = cluster_centers[other_cluster]
                        dist = self.haversine_distance(
                            outlet['latitude'], outlet['longitude'],
                            center_lat, center_lon
                        )
                        
                        if dist <= self.max_merge_distance_km and dist < min_distance:
                            min_distance = dist
                            nearest_cluster = other_cluster
                    
                    if nearest_cluster is not None:
                        result.loc[idx, 'cluster'] = nearest_cluster
                        changes_made = True
                        
                        outlets_in_cluster = result[result['cluster'] == nearest_cluster]
                        lats = outlets_in_cluster['latitude'].values
                        lons = outlets_in_cluster['longitude'].values
                        cluster_centers[nearest_cluster] = (np.mean(lats), np.mean(lons))
            
            if changes_made:
                cluster_centers = defaultdict(list)
                for idx, row in result.iterrows():
                    if row['latitude'] != 0 and row['longitude'] != 0:
                        cluster_centers[row['cluster']].append((row['latitude'], row['longitude']))
                
                for cluster in cluster_centers:
                    lats = [coord[0] for coord in cluster_centers[cluster]]
                    lons = [coord[1] for coord in cluster_centers[cluster]]
                    cluster_centers[cluster] = (np.mean(lats), np.mean(lons))
                
                result['center_lat'] = result['cluster'].map(lambda x: cluster_centers.get(x, (0, 0))[0])
                result['center_lon'] = result['cluster'].map(lambda x: cluster_centers.get(x, (0, 0))[1])
                
                result['distance_to_center_km'] = result.apply(
                    lambda row: self.haversine_distance(
                        row['latitude'], row['longitude'],
                        row['center_lat'], row['center_lon']
                    ) if row['latitude'] != 0 and row['longitude'] != 0 else 0, 
                    axis=1
                )
        
        cluster_counts = result['cluster'].value_counts()
        single_outlet_clusters = cluster_counts[cluster_counts < self.min_outlets_per_cluster].index.tolist()
        
        if single_outlet_clusters:
            single_cluster_matrix = {}
            for i, cluster1 in enumerate(single_outlet_clusters):
                single_cluster_matrix[cluster1] = {}
                outlet1 = result[result['cluster'] == cluster1].iloc[0]
                
                for cluster2 in single_outlet_clusters:
                    if cluster1 == cluster2:
                        continue
                        
                    outlet2 = result[result['cluster'] == cluster2].iloc[0]
                    dist = self.haversine_distance(
                        outlet1['latitude'], outlet1['longitude'],
                        outlet2['latitude'], outlet2['longitude']
                    )
                    single_cluster_matrix[cluster1][cluster2] = dist
            
            merged_clusters = set()
            for cluster1 in single_outlet_clusters:
                if cluster1 in merged_clusters:
                    continue
                    
                nearest_cluster = None
                min_distance = float('inf')
                
                for cluster2, dist in single_cluster_matrix[cluster1].items():
                    if cluster2 in merged_clusters:
                        continue
                        
                    if dist <= self.max_merge_distance_km and dist < min_distance:
                        min_distance = dist
                        nearest_cluster = cluster2
                
                if nearest_cluster is not None:
                    result.loc[result['cluster'] == nearest_cluster, 'cluster'] = cluster1
                    merged_clusters.add(nearest_cluster)
                    
                    outlets_in_cluster = result[result['cluster'] == cluster1]
                    lats = outlets_in_cluster['latitude'].values
                    lons = outlets_in_cluster['longitude'].values
                    cluster_centers[cluster1] = (np.mean(lats), np.mean(lons))
            
            if merged_clusters:
                cluster_centers = defaultdict(list)
                for idx, row in result.iterrows():
                    if row['latitude'] != 0 and row['longitude'] != 0:
                        cluster_centers[row['cluster']].append((row['latitude'], row['longitude']))
                
                for cluster in cluster_centers:
                    lats = [coord[0] for coord in cluster_centers[cluster]]
                    lons = [coord[1] for coord in cluster_centers[cluster]]
                    cluster_centers[cluster] = (np.mean(lats), np.mean(lons))
                
                result['center_lat'] = result['cluster'].map(lambda x: cluster_centers.get(x, (0, 0))[0])
                result['center_lon'] = result['cluster'].map(lambda x: cluster_centers.get(x, (0, 0))[1])
                
                result['distance_to_center_km'] = result.apply(
                    lambda row: self.haversine_distance(
                        row['latitude'], row['longitude'],
                        row['center_lat'], row['center_lon']
                    ) if row['latitude'] != 0 and row['longitude'] != 0 else 0, 
                    axis=1
                )
        
        cluster_counts = result['cluster'].value_counts()
        single_outlet_clusters = cluster_counts[cluster_counts < self.min_outlets_per_cluster].index.tolist()
        
        if single_outlet_clusters:
            for single_cluster in single_outlet_clusters:
                single_outlet = result[result['cluster'] == single_cluster].iloc[0]
                min_distance = float('inf')
                nearest_cluster = None
                
                for other_cluster, count in cluster_counts.items():
                    if other_cluster != single_cluster and count >= self.min_outlets_per_cluster:
                        center_lat, center_lon = cluster_centers.get(other_cluster, (0, 0))
                        dist = self.haversine_distance(
                            single_outlet['latitude'], single_outlet['longitude'],
                            center_lat, center_lon
                        )
                        if dist < min_distance:
                            min_distance = dist
                            nearest_cluster = other_cluster
                
                if nearest_cluster is not None and min_distance <= self.max_merge_distance_km:
                    result.loc[result['cluster'] == single_cluster, 'cluster'] = nearest_cluster
                    
                    outlets_in_cluster = result[result['cluster'] == nearest_cluster]
                    lats = outlets_in_cluster['latitude'].values
                    lons = outlets_in_cluster['longitude'].values
                    cluster_centers[nearest_cluster] = (np.mean(lats), np.mean(lons))
        
        cluster_centers = defaultdict(list)
        for idx, row in result.iterrows():
            if row['latitude'] != 0 and row['longitude'] != 0:
                cluster_centers[row['cluster']].append((row['latitude'], row['longitude']))
        
        for cluster in cluster_centers:
            lats = [coord[0] for coord in cluster_centers[cluster]]
            lons = [coord[1] for coord in cluster_centers[cluster]]
            cluster_centers[cluster] = (np.mean(lats), np.mean(lons))
        
        result['center_lat'] = result['cluster'].map(lambda x: cluster_centers.get(x, (0, 0))[0])
        result['center_lon'] = result['cluster'].map(lambda x: cluster_centers.get(x, (0, 0))[1])
        
        result['distance_to_center_km'] = result.apply(
            lambda row: self.haversine_distance(
                row['latitude'], row['longitude'],
                row['center_lat'], row['center_lon']
            ) if row['latitude'] != 0 and row['longitude'] != 0 else 0, 
            axis=1
        )

        cluster_mapping = {}
        for i, cluster in enumerate(result['cluster'].unique(), 1):
            cluster_mapping[cluster] = i
        
        result['cluster'] = result['cluster'].map(cluster_mapping)
        
        new_cluster_centers = {}
        for old_cluster, new_cluster in cluster_mapping.items():
            new_cluster_centers[new_cluster] = cluster_centers[old_cluster]

        cluster_centers = new_cluster_centers
        
        print(f"\nHasil pengelompokan outlet dengan radius {self.radius_km} km:")
        print(f"Jumlah cluster: {result['cluster'].nunique()}")
        print(f"Jumlah outlet: {len(result)}")

        cluster_counts = result['cluster'].value_counts().reset_index()
        cluster_counts.columns = ['cluster', 'jumlah_outlet']
        print(f"\nDistribusi jumlah outlet per cluster:")
        print(f"Minimum: {cluster_counts['jumlah_outlet'].min()} outlet")
        print(f"Maksimum: {cluster_counts['jumlah_outlet'].max()} outlet")
        print(f"Rata-rata: {cluster_counts['jumlah_outlet'].mean():.1f} outlet")

        print(f"\nStatistik jarak outlet ke pusat cluster:")
        print(f"Jarak minimum: {result['distance_to_center_km'].min():.2f} km")
        print(f"Jarak maksimum: {result['distance_to_center_km'].max():.2f} km")
        print(f"Jarak rata-rata: {result['distance_to_center_km'].mean():.2f} km")

        return result
