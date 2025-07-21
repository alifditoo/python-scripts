import time
import pandas as pd
import re
from urllib3.exceptions import *
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import *
from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchWindowException, InvalidSessionIdException, WebDriverException
from requests.exceptions import ReadTimeout as ReadTimeoutError

#-- Headless Mode --#
browser_options = Options()
browser_options.add_argument("start-minimized")
# browser_options.add_argument("--headless=new")

#-- Define Function --#
def get_product_link_from_page(soup, result_elements):
    current_element = soup.find("div", id="zeus-root")
    soup = current_element

    classes = ["css-8atqhb", "css-jau1bt", "css-rjanld"]

    for class_ in classes:
        current_element = soup.find("div", class_=class_)
        soup = current_element

    current_element = soup.find(attrs={"data-testid": "divSRPContentProducts"})
    soup = current_element

    try:
        current_elements = soup.find_all("div", class_="css-jza1fo")
        soup = current_elements
    except AttributeError:
        pass
    else:
        pass

    if soup is not None:
        for element in soup:
            sub_elements = element.find_all("div", class_="css-5wh65g")
            for child_element in sub_elements:
                child_element = child_element.find("a")
                if child_element is not None:
                    product_link = child_element.get("href")
                    spans = child_element.find_all("span")
                    product_name = None
                    for span in spans:
                        if span.text and span.text.strip() and len(span.text.strip()) >= 8:
                            product_name = span
                            break

                    if product_name is None:
                        longest_text = ""
                        for span in spans:
                            if span.text and span.text.strip() and len(span.text.strip()) > len(longest_text):
                                longest_text = span.text.strip()
                                product_name = span
                    result_elements.append((product_name.text, product_link))
    else:
        pass

    return result_elements

def get_page_source(website_link):
    driver = WebDriver(options=browser_options)
    page_resources = []
    try:
        driver.get(website_link)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#zeus-root")))
        time.sleep(1)
        
        try:
            popup_element = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".css-dfpqc0"))
            )
            if popup_element:
                close_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".css-11hzwo5"))
                )
                close_button.click()
                time.sleep(0.5)
        except:
            pass
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        try:
            list_of_variant = soup.find_all("div", class_="css-hayuji")
        except:
            list_of_variant = None
        
        if len(list_of_variant) == 0:
            page_resources.append(driver.page_source)
        elif len(list_of_variant) == 1:
            for variant in list_of_variant:
                active_variants = variant.find_all("div", {'data-testid': ['btnVariantChipActive', 'btnVariantChipActiveSelected']})
                for active_variant in active_variants:
                    buttons = active_variant.find_all('button')
                    for button in buttons:
                        try:
                            button_element = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, f"//button[text()='{button.text}']"))
                            )
                            button_element.click()
                            time.sleep(1)
                            page_resources.append(driver.page_source)
                        except Exception as e:
                            pass
                            # print(f"Gagal mengklik button {button.text}: {str(e)}")
        elif len(list_of_variant) == 2:
            for variant in [list_of_variant[0]]:
                active_variants = variant.find_all("div", {'data-testid': ['btnVariantChipActive', 'btnVariantChipActiveSelected']})
                for active_variant in active_variants:
                    buttons = active_variant.find_all('button')
                    for button in buttons:
                        try:
                            button_element = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, f"//button[text()='{button.text}']"))
                            )
                            button_element.click()
                            # Get Sub Variant
                            per_variant_page_source = driver.page_source
                            variant_soup = BeautifulSoup(per_variant_page_source, 'html.parser')
                            sub_variant = variant_soup.find_all("div", class_="css-hayuji")
                            for sub_variant in [sub_variant[1]]:
                                active_variants = sub_variant.find_all("div", {'data-testid': ['btnVariantChipActive', 'btnVariantChipActiveSelected']})
                                for active_variant in active_variants:
                                    subvariant_buttons = active_variant.find_all('button')
                                    for subvariant_button in subvariant_buttons:
                                        try:
                                            subvariant_button_element = WebDriverWait(driver, 10).until(
                                                EC.element_to_be_clickable((By.XPATH, f"//button[text()='{subvariant_button.text}']"))
                                            )
                                            subvariant_button_element.click()
                                            time.sleep(1)
                                            page_resources.append(driver.page_source)
                                        except Exception as e:
                                            pass
                                            # print(f"Gagal mengklik button {subvariant_button.text}: {str(e)}")
                            time.sleep(1)
                        except Exception as e:
                            pass
                            # print(f"Gagal mengklik button {button.text}: {str(e)}")
        return page_resources
    except (NoSuchWindowException, ReadTimeoutError, InvalidSessionIdException, WebDriverException) as e:
        if driver:
            driver.quit()
        raise Exception(f'Error: {str(e)}')
    finally:
        if driver:
            driver.quit()
            

def search(query, page_start, page_end):
    temporary_elements = [('Nama Produk', 'Link Produk')]
    page_range = range(page_start, page_end)
    query = query.replace(" ", "+")
    for m in page_range:
        driver = WebDriver(options=browser_options)
        try:
            driver.get("https://www.tokopedia.com/search?navsource=&page={}&q={}".format(m + 1, query))
        except NoSuchWindowException:
            continue
        except ReadTimeoutError:
            break

        scripts = []
        try:
            for k in range(80):
                driver.execute_script("window.scrollBy({}, {});".format(k, k + 1))
                time.sleep(0.05)
                if 30 <= k <= 50:
                    scripts.append(driver.page_source)
            if datetime.now().second < 60:
                # time.sleep(60.0 - float(datetime.now().second))
                time.sleep(3)
                scripts.append(driver.page_source)
            else:
                time.sleep(0.0)
                scripts.append(driver.page_source)
        except NoSuchWindowException:
            driver.close()
            continue
        except ReadTimeoutError:
            driver.close()
            continue
        except InvalidSessionIdException:
            driver.close()
            continue
        except WebDriverException:
            driver.close()
            continue
        else:
            driver.close()
            for script in scripts:
                soup = BeautifulSoup(script, 'html.parser')
                temporary_elements = get_product_link_from_page(soup, temporary_elements)
                continue
        finally:
            driver.quit()
    return list(temporary_elements)

def get_product_link(query, page_start=0, page_end=1):
    result = search(query, page_start, page_end)
    df_result = pd.DataFrame(result[1:], columns=result[0])
    df_result = df_result.drop_duplicates(subset=['Link Produk'], keep='first').reset_index(drop=True)
    return df_result

def save_to_file(dataframe, file_name, file_format='csv'):
    '''
    Save the DataFrame to a file in the specified format.
    
    Parameters:
    dataframe (pd.DataFrame): The DataFrame to save.
    file_name (str): The name of the file to save the data to (without extension).
    file_format (str): The format to save the file in ('csv' or 'xlsx'). Default is 'csv'.
    '''
    if file_format == 'csv':
        dataframe.to_csv(f"{file_name}.csv", index=False)
    elif file_format == 'xlsx':
        dataframe.to_excel(f"{file_name}.xlsx", index=False)
    else:
        raise ValueError("Unknown file format. Choose 'csv' or 'xlsx'.")

list_of_products = [''] #<-- Input Product Name Here

final_result = []
for product in list_of_products:
    df_result = get_product_link(product)
    for index, row in df_result.iterrows():
        product_link = row['Link Produk']
        page_resources = get_page_source(product_link)
        for page_resource in page_resources:
            data_found = {}
            soup = BeautifulSoup(page_resource, 'html.parser')
            scripts = soup.find_all('script', type='text/javascript')

            #-- Title --#
            try:
                title = soup.find('h1', {'data-testid': 'lblPDPDetailProductName'}).text.strip()
            except AttributeError:
                title = ''
            #-- Variant Selected --#
            try:
                variant_selected = ' - '.join([variant.text for variant in soup.find_all('div', {'data-testid': 'btnVariantChipActiveSelected'})])
            except AttributeError:
                variant_selected = ''
            #-- Rating --#
            try:
                rating = soup.find('span', {'data-testid': 'lblPDPDetailProductRatingNumber'}).text
            except AttributeError:
                rating = ''
            #-- Condition --#
            try:
                for content in soup.find('ul', {'data-testid': 'lblPDPInfoProduk'}).contents:
                    if 'Kondisi' in content.text:
                        item_condition = content.text.split('Kondisi:')[-1].strip()
            except AttributeError:
                item_condition = ''
            #-- Price --#
            try:
                price = soup.find('div', {'data-testid': 'lblPDPDetailProductPrice'}).text.replace('Rp', '').replace('.', '')
            except AttributeError:
                price = ''
            #-- Count Sold --#
            try:
                for script in scripts:
                    if script.string and 'countSold' in script.string:
                        match = re.search(r'"countSold"\s*:\s*"?(\d+)"?', script.string)
                        if match:
                            sold = match.group(1)
                        else:
                            sold = soup.find('p', {'data-testid': 'lblPDPDetailProductSoldCounter'}).text.replace("Terjual", "").replace('rb+', "000").replace(" ", "").replace("+", "").replace("barangberhasilterjual", '')
            except AttributeError:
                sold = ''
            try:
                description = soup.find('div', {'data-testid': 'lblPDPDescriptionProduk'}).text.strip().replace("\n", " ")
            except AttributeError:
                description = ''
            #-- Shop Name --#
            try:
                shop_name = soup.find('h2', class_='css-1ceqk3d-unf-heading e1qvo2ff2').text.strip()
            except AttributeError:
                shop_name = ''
            #-- Store Location --#
            try:
                store_location = soup.find('h2', class_='css-793nib-unf-heading e1qvo2ff2').text.replace('Dikirim dari', '').strip()
            except AttributeError:
                store_location = ''
            data_found['keyword'] = product
            data_found['title'] = title
            data_found['variant'] = variant_selected
            data_found['rating'] = rating
            data_found['price'] = price
            data_found['sold'] = sold
            data_found['description'] = description
            data_found['item_condition'] = item_condition
            data_found['shop_name'] = shop_name
            data_found['store_location'] = store_location
            data_found['product_site'] = product_link
            data_found['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            final_result.append(data_found)

df_productdetails = pd.DataFrame(final_result)
df_productdetails.replace('', None, inplace=True)
save_to_file(df_productdetails, 'product_details', file_format='xlsx')
