# 🗺️ Outlet Geographic Clustering

A Python module to cluster retail outlets based on their **latitude and longitude** coordinates. It uses a **multi-phase hierarchical clustering algorithm** with distance constraints to ensure all outlets in a cluster are geographically cohesive.

---

## 📌 Overview

This module is designed for **efficient geographic distribution analysis** of retail outlets. It helps businesses group nearby outlets based on location to optimize field operations, delivery, and market strategy.

---

## 🧠 Key Components

### 🧱 `OutletClustering` Class
Encapsulates the clustering logic with configurable parameters:

| Parameter                   | Description                                               | Default  |
|----------------------------|-----------------------------------------------------------|----------|
| `radius_km`                | Max radius (in km) allowed within a cluster               | `8 km`   |
| `min_outlets_per_cluster`  | Minimum outlets required to form a cluster                | `2`      |
| `max_merge_distance_km`    | Max distance to merge small/isolated clusters             | `20 km`  |

---

## 📏 Distance Calculation

- Uses the **Haversine formula** for geospatial distance.
- Accurately considers **Earth's curvature**.
- Generates a full distance matrix between all points.

---

## 🔄 Clustering Algorithm

### `group_outlets_by_radius()` Method

Performs a robust multi-step clustering process:

#### 1. Initial Clustering
- Filters out invalid coordinates.
- Computes a distance matrix.
- Runs `AgglomerativeClustering` with `threshold = 0.5 * radius_km`.

#### 2. Cluster Refinement
- Computes each cluster’s geometric center.
- Separates outlets farther than `radius_km` from the center.

#### 3. Cluster Optimization
- Detects clusters with fewer than `min_outlets_per_cluster`.
- Merges them with nearby larger clusters if within `max_merge_distance_km`.
- Handles special cases for isolated outlets.

---

## 📤 Output

Returns a pandas `DataFrame` with the following columns:

- `outlet_id`
- `latitude`
- `longitude`
- `cluster`
- `center_lat`
- `center_lon`
- `distance_to_center_km`

Also prints summary statistics:
- Total number of clusters
- Distribution of outlet counts per cluster
- Distance stats (min, max, mean)

---

## 🚀 Usage Example

```python
from outlet_clustering import OutletClustering

# Initialize clustering with custom parameters
clusterer = OutletClustering(
    radius_km=10,
    min_outlets_per_cluster=3,
    max_merge_distance_km=25
)

# Your DataFrame must include: 'outlet_id', 'latitude', 'longitude'
result_df = clusterer.group_outlets_by_radius(outlets_df)

# Save the result to CSV
result_df.to_csv("outlet_clusters.csv", index=False)
```

---

## 🧭 Applications

This algorithm is particularly useful for:

- 🧑‍💼 **Territory management** (sales, field ops)
- 📦 **Delivery & logistics zone planning**
- 🏪 **Retail outlet network optimization**
- 📈 **Market expansion strategy**
- 📊 **Location-based customer segmentation**

---

## 📦 Dependencies

You’ll need the following Python libraries:

```bash
pip install pandas numpy scikit-learn
```

This module also uses:

- `math` – for Haversine distance calculation  
- `scipy.spatial.distance`  
- `sklearn.cluster.AgglomerativeClustering`
