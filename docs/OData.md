---
title: "OData – Documentation"
source: "https://documentation.dataspace.copernicus.eu/APIs/OData.html"

---
OData is an SO/IEC approved, OASIS standard, which is based on https RESTful Application Programming Interfaces. It enables resources, which are identified by URLs and defined in a data model, to be created and edited using simple HTTPS messages. OData makes it possible to build REST-based data services that let Web clients publish and edit resources that are recognized by Uniform Resource Locators (URLs) and described in a data model using straightforward HTTPS messages.

## OData Products endpoint

Tip

Crucial for the search performance is specifying the collection name. Example: Collection/Name eq ‘SENTINEL-3’

The additional efficient way to accelerate the query performance is limiting the query by acquisition dates, e.g.: ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-21T00:00:00.000Z

When searching for products and adding a wide range of dates to the query, e.g. from 2017 to 2023, we recommend splitting the query into individual years, e.g. from January 1, 2023 to December 31, 2023.

Tip

To ensure efficient and permanent querying of the Copernicus Data Space Ecosystem Catalogue, it is highly recommended to utilize [OData Subscriptions](https://documentation.dataspace.copernicus.eu/APIs/Subscriptions.html). These subscriptions provide the most effective way to stay informed about newly added products in the catalogue.

The primary objective of Subscription Services is to enable users to receive real-time notifications about relevant events occurring within the Copernicus Data Space Ecosystem Catalogue. Users can tailor their notifications by specifying filtering parameters in the subscription request.

A dedicated section provides comprehensive information to guide users through the implementation process: [OData Subscriptions](https://documentation.dataspace.copernicus.eu/APIs/Subscriptions.html).

### Query structure

As a general note, the OData query consists of elements which in this documentation are called “options”. The interface supports the following search options:

- filter
- orderby
- top
- skip
- count
- expand

Search options should always be preceded with *$* and consecutive options should be separated with *&*.

Consecutive filters within *filter* option should be separated with *and* or *or*. *Not* operator can also be used e.g.:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=not (Collection/Name eq 'SENTINEL-2') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T00:10:00.000Z&$orderby=ContentDate/Start&$top=100`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=not%20\(Collection/Name%20eq%20%27SENTINEL-2%27\)%20and%20ContentDate/Start%20gt%202022-05-03T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-05-03T00:10:00.000Z&$orderby=ContentDate/Start&$top=100)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=not (Collection/Name eq 'SENTINEL-2') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T00:10:00.000Z&$orderby=ContentDate/Start&$top=100").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 2a92387c-d802-4ac7-9b24-187e0e6d8ab4 | c\_gls\_LIE250\_202205030000\_Baltic\_MODIS\_V1.2.2\_nc | /eodata/CLMS/bio-geophysical/river\_and\_lake\_ic... | {'type': 'Polygon', 'coordinates': \[\[\[4.99625,... |
| --- | --- | --- | --- | --- |
| 1 | 1d42f2d3-2456-485f-a93e-92f08bdd5c51 | S1A\_OPER\_AUX\_GNSSRD\_POD\_\_20220510T020122\_V2022... | /eodata/Sentinel-1/AUX/AUX\_GNSSRD/2022/05/03/S... | None |
| 2 | 5c744d5c-c082-4a34-a181-81cde73cd25d | S1B\_OPER\_AUX\_GNSSRD\_POD\_\_20220510T023113\_V2022... | /eodata/Sentinel-1/AUX/AUX\_GNSSRD/2022/05/03/S... | None |

## Filter option

### Query by name

To search for a specific product by its exact name:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'S1A_IW_GRDH_1SDV_20141031T161924_20141031T161949_003076_003856_634E.SAFE'`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name%20eq%20%27S1A_IW_GRDH_1SDV_20141031T161924_20141031T161949_003076_003856_634E.SAFE%27)

To search for Copernicus Contributing Mission (CCM) data:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name eq 'SP07_NAO_MS4_2A_20210729T064948_20210729T064958_TOU_1234_90f0.DIMA'&$expand=Attributes`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Name%20eq%20%27SP07_NAO_MS4_2A_20210729T064948_20210729T064958_TOU_1234_90f0.DIMA%27&$expand=Attributes)

Alternatively *contains*, *endswith* and *startswith* can be used to search for products ending or starting with provided string. You should use *Collection/Name* filter even if it overlaps with *startswith* or *contains* clause.

### Query by list

In case a user desires to search for multiple products by name in one query, the POST method can be used:

**POST**

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products/OData.CSC.FilterList`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products/OData.CSC.FilterList)

**Request body**:

```
{
  "FilterProducts":
    [
     {"Name": "S1A_IW_GRDH_1SDV_20141031T161924_20141031T161949_003076_003856_634E.SAFE"},
     {"Name": "S3B_SL_1_RBT____20190116T050535_20190116T050835_20190117T125958_0179_021_048_0000_LN2_O_NT_003.SEN3"},
     {"Name": "xxxxxxxx.06.tar"}
    ]
 }
```

Two results are returned, as there is no product named xxxxxxxx.06.tar.

### Query Collection of Products

To search for products within a specific collection:

For Sentinel-2:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-2'`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-2%27)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-2'").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 2d8eb355-3930-4a6f-b02c-f793773cb656 | S2A\_OPER\_AUX\_GNSSRD\_POD\_\_20171211T085826\_V2015... | /eodata/Sentinel-2/AUX/AUX\_GNSSRD/2015/06/27/S... | None |
| --- | --- | --- | --- | --- |
| 1 | 5303fa53-2dd4-4ee2-b012-d123a2ccd0b4 | S2A\_OPER\_AUX\_GNSSRD\_POD\_\_20171211T085921\_V2015... | /eodata/Sentinel-2/AUX/AUX\_GNSSRD/2015/06/28/S... | None |
| 2 | 92dc2be7-c737-4472-890a-2dc5da28e9c0 | S2A\_OPER\_AUX\_GNSSRD\_POD\_\_20171211T093809\_V2015... | /eodata/Sentinel-2/AUX/AUX\_GNSSRD/2015/07/29/S... | None |

For Copernicus Contributing Missions (CCM):

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'CCM'`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27CCM%27)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'CCM'").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 70c20650-4621-40ee-9f29-41973e8ef96b | DEM1\_SAR\_DTE\_90\_20110204T132020\_20141115T13303... | /eodata/CCM/COP-DEM\_GLO-90-DTED/SAR\_DTE\_90\_61F... | {'type': 'Polygon', 'coordinates': \[\[\[59.0, 68... |
| --- | --- | --- | --- | --- |
| 1 | aabba86a-53ef-4c17-a673-ecda83e13203 | DEM1\_SAR\_DTE\_90\_20110204T091108\_20131220T09231... | /eodata/CCM/COP-DEM\_GLO-90-DTED/SAR\_DTE\_90\_61F... | {'type': 'Polygon', 'coordinates': \[\[\[-58.0, -... |
| 2 | 00646e04-06e0-4462-9ef4-cf3128abda61 | PH1B\_PHR\_MS\_\_2A\_20180920T141019\_20180920T14102... | /eodata/CCM/VHR\_IMAGE\_2018/PHR\_MS\_\_2A\_E1F0/201... | {'type': 'Polygon', 'coordinates': \[\[\[-52.7024... |

The following collections are currently available:

- Copernicus Sentinel Mission
	- **SENTINEL-1**
	- **SENTINEL-2**
	- **SENTINEL-3**
	- **SENTINEL-5P**
	- **SENTINEL-6**
	- **SENTINEL-1-RTC** (Sentinel-1 Radiometric Terrain Corrected)
- Complementary data
	- **GLOBAL-MOSAICS** (Sentinel-1 and Sentinel-2 Global Mosaics)
	- **SMOS** (Soil Moisture and Ocean Salinity)
	- **ENVISAT** (ENVISAT- Medium Resolution Imaging Spectrometer - MERIS)
	- **LANDSAT-5**
	- **LANDSAT-7**
	- **LANDSAT-8**
	- **COP-DEM** (Copernicus DEM)
	- **TERRAAQUA** (Terra MODIS and Aqua MODIS)
	- **S2GLC** (S2GLC 2017)
- Copernicus Contributing Missions (CCM)

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'CCM' and ContentDate/Start gt 2005-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T00:11:00.000Z`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27CCM%27%20and%20ContentDate/Start%20gt%202005-05-03T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-05-03T00:11:00.000Z)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'CCM' and ContentDate/Start gt 2005-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T00:11:00.000Z").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 00000298-7cca-4002-bd6c-cdd7d40cf94e | DEM1\_SAR\_DGE\_10\_20101224T155413\_20130403T15484... | /eodata/CCM/COP-DEM\_EEA-10-DGED/SAR\_DGE\_10\_931... | {'type': 'Polygon', 'coordinates': \[\[\[24.0, 64... |
| --- | --- | --- | --- | --- |
| 1 | 00000594-e5c6-40e6-8c8a-d1dfabf2c98e | EW03\_WV3\_PM4\_OR\_20150810T092701\_20150810T09271... | /eodata/CCM/VHR\_IMAGE\_2015/WV3\_PM4\_OR\_71F4/201... | {'type': 'Polygon', 'coordinates': \[\[\[29.02003... |
| 2 | 00000e4d-be6d-41e0-b5fa-bbacedfa4646 | DEM1\_SAR\_DTE\_30\_20130608T084201\_20140731T00573... | /eodata/CCM/COP-DEM\_GLO-30-DTED/SAR\_DTE\_30\_615... | {'type': 'Polygon', 'coordinates': \[\[\[-71.0, -... |

### Query by Sensing Date

To search for products acquired between two dates:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=ContentDate/Start gt 2019-05-15T00:00:00.000Z and ContentDate/Start lt 2019-05-16T00:00:00.000Z`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=ContentDate/Start%20gt%202019-05-15T00:00:00.000Z%20and%20ContentDate/Start%20lt%202019-05-16T00:00:00.000Z)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=ContentDate/Start gt 2019-05-15T00:00:00.000Z and ContentDate/Start lt 2019-05-16T00:00:00.000Z").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 4725d436-3e90-5480-bee1-0f13a7fc14fd | S3B\_SL\_1\_RBT\_\_\_\_20190515T000040\_20190515T00034... | /eodata/Sentinel-3/SLSTR/SL\_1\_RBT/2019/05/15/S... | {'type': 'Polygon', 'coordinates': \[\[\[-8.40421... |
| --- | --- | --- | --- | --- |
| 1 | 169fda08-9928-576e-a556-97a6d3b9bacf | S3B\_SL\_1\_RBT\_\_\_\_20190515T000040\_20190515T00034... | /eodata/Sentinel-3/SLSTR/SL\_1\_RBT/2019/05/15/S... | {'type': 'Polygon', 'coordinates': \[\[\[-8.40421... |
| 2 | 07c0c999-5f9d-553f-9b3d-f2b8ab013856 | S3B\_SL\_2\_LST\_\_\_\_20190515T000040\_20190515T00034... | /eodata/Sentinel-3/SLSTR/SL\_2\_LST/2019/05/15/S... | {'type': 'Polygon', 'coordinates': \[\[\[-8.40421... |

As an example, for the Copernicus Contributions Mission Data (CCM):

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'CCM' and OData.CSC.Intersects(area=geography'SRID=4326;POLYGON((12.655118166047592 47.44667197521409,21.39065656328509 48.347694733853245,28.334291357162826 41.877123516783655,17.47086198383573 40.35854475076158,12.655118166047592 47.44667197521409))') and ContentDate/Start gt 2021-05-20T00:00:00.000Z and ContentDate/Start lt 2021-07-21T00:00:00.000Z`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27CCM%27%20and%20OData.CSC.Intersects\(area=geography%27SRID=4326;POLYGON\(\(12.655118166047592%2047.44667197521409,21.39065656328509%2048.347694733853245,28.334291357162826%2041.877123516783655,17.47086198383573%2040.35854475076158,12.655118166047592%2047.44667197521409\)\)%27\)%20and%20ContentDate/Start%20gt%202021-05-20T00:00:00.000Z%20and%20ContentDate/Start%20lt%202021-07-21T00:00:00.000Z)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'CCM' and OData.CSC.Intersects(area=geography'SRID=4326;POLYGON((12.655118166047592 47.44667197521409,21.39065656328509 48.347694733853245,28.334291357162826 41.877123516783655,17.47086198383573 40.35854475076158,12.655118166047592 47.44667197521409))') and ContentDate/Start gt 2021-05-20T00:00:00.000Z and ContentDate/Start lt 2021-07-21T00:00:00.000Z").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 19db5dbf-d394-4e7b-a7aa-b0d2629cbe68 | PH1B\_PHR\_MS\_\_2A\_20210603T095945\_20210603T09594... | /eodata/CCM/VHR\_IMAGE\_2021/PHR\_MS\_\_2A\_07B6/202... | {'type': 'Polygon', 'coordinates': \[\[\[16.87990... |
| --- | --- | --- | --- | --- |
| 1 | 6c742dca-e0d6-4182-ae66-6ba5ecdfd9ce | SW00\_OPT\_MS4\_1B\_20210603T094047\_20210603T09405... | /eodata/CCM/VHR\_IMAGE\_2021/OPT\_MS4\_1B\_07B6/202... | {'type': 'Polygon', 'coordinates': \[\[\[19.99165... |
| 2 | 2692ef4a-3b3e-4ebc-829c-ab6a288b7820 | SW00\_OPT\_MS4\_1B\_20210603T094631\_20210603T09463... | /eodata/CCM/VHR\_IMAGE\_2021/OPT\_MS4\_1B\_07B6/202... | {'type': 'Polygon', 'coordinates': \[\[\[22.99911... |

Usually, there are two parameters describing the ContentDate (Acquisition Dates) for a product - Start and End. Depending on what the user is looking for, these parameters can be mixed, e.g.:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=ContentDate/Start gt 2019-05-15T00:00:00.000Z and ContentDate/End lt 2019-05-15T00:05:00.000Z`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=ContentDate/Start%20gt%202019-05-15T00:00:00.000Z%20and%20ContentDate/End%20lt%202019-05-15T00:05:00.000Z)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=ContentDate/Start gt 2019-05-15T00:00:00.000Z and ContentDate/End lt 2019-05-15T00:05:00.000Z").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 4725d436-3e90-5480-bee1-0f13a7fc14fd | S3B\_SL\_1\_RBT\_\_\_\_20190515T000040\_20190515T00034... | /eodata/Sentinel-3/SLSTR/SL\_1\_RBT/2019/05/15/S... | {'type': 'Polygon', 'coordinates': \[\[\[-8.40421... |
| --- | --- | --- | --- | --- |
| 1 | 169fda08-9928-576e-a556-97a6d3b9bacf | S3B\_SL\_1\_RBT\_\_\_\_20190515T000040\_20190515T00034... | /eodata/Sentinel-3/SLSTR/SL\_1\_RBT/2019/05/15/S... | {'type': 'Polygon', 'coordinates': \[\[\[-8.40421... |
| 2 | 07c0c999-5f9d-553f-9b3d-f2b8ab013856 | S3B\_SL\_2\_LST\_\_\_\_20190515T000040\_20190515T00034... | /eodata/Sentinel-3/SLSTR/SL\_2\_LST/2019/05/15/S... | {'type': 'Polygon', 'coordinates': \[\[\[-8.40421... |

Tip

Filtering by ContentDate/Start is much faster than by ContentDate/End for big collections. Narrowing ContentDate/Start gives the best performance boost for *SENTINEL-2* collection.

### Query by Geographic Criteria

To search for products intersecting the specified polygon:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=OData.CSC.Intersects(area=geography'SRID=4326;POLYGON((12.655118166047592 47.44667197521409,21.39065656328509 48.347694733853245,28.334291357162826 41.877123516783655,17.47086198383573 40.35854475076158,12.655118166047592 47.44667197521409))') and ContentDate/Start gt 2022-05-20T00:00:00.000Z and ContentDate/Start lt 2022-05-21T00:00:00.000Z`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=OData.CSC.Intersects\(area=geography%27SRID=4326;POLYGON\(\(12.655118166047592%2047.44667197521409,21.39065656328509%2048.347694733853245,28.334291357162826%2041.877123516783655,17.47086198383573%2040.35854475076158,12.655118166047592%2047.44667197521409\)\)%27\)%20and%20ContentDate/Start%20gt%202022-05-20T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-05-21T00:00:00.000Z)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=OData.CSC.Intersects(area=geography'SRID=4326;POLYGON((12.655118166047592 47.44667197521409,21.39065656328509 48.347694733853245,28.334291357162826 41.877123516783655,17.47086198383573 40.35854475076158,12.655118166047592 47.44667197521409))') and ContentDate/Start gt 2022-05-20T00:00:00.000Z and ContentDate/Start lt 2022-05-21T00:00:00.000Z").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | e73c2a1c-a421-4d19-b265-8e1462a60b43 | c\_gls\_LIE250\_202205200000\_Baltic\_MODIS\_V1.2.2\_nc | /eodata/CLMS/bio-geophysical/river\_and\_lake\_ic... | {'type': 'Polygon', 'coordinates': \[\[\[4.99625,... |
| --- | --- | --- | --- | --- |
| 1 | 48c6e950-d2cf-4c58-afb4-3cc346c39c20 | c\_gls\_SCE\_202205200000\_NHEMI\_SLSTR\_V1.0.1\_nc | /eodata/CLMS/bio-geophysical/snow\_cover\_extent... | {'type': 'Polygon', 'coordinates': \[\[\[-180.0,... |
| 2 | 115d99f1-f91c-49c8-a569-962c365933a1 | c\_gls\_SCE\_202205200000\_NHEMI\_VIIRS\_V1.0.1\_nc | /eodata/CLMS/bio-geophysical/snow\_cover\_extent... | {'type': 'Polygon', 'coordinates': \[\[\[-180.0,... |

Similarly, for the Copernicus Contributing Missions (CCM) data:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'CCM' and OData.CSC.Intersects(area=geography'SRID=4326;POLYGON((12.655118166047592 47.44667197521409,21.39065656328509 48.347694733853245,28.334291357162826 41.877123516783655,17.47086198383573 40.35854475076158,12.655118166047592 47.44667197521409))')&$top=20`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27CCM%27%20and%20OData.CSC.Intersects\(area=geography%27SRID=4326;POLYGON\(\(12.655118166047592%2047.44667197521409,21.39065656328509%2048.347694733853245,28.334291357162826%2041.877123516783655,17.47086198383573%2040.35854475076158,12.655118166047592%2047.44667197521409\)\)%27\)&$top=20)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'CCM' and OData.CSC.Intersects(area=geography'SRID=4326;POLYGON((12.655118166047592 47.44667197521409,21.39065656328509 48.347694733853245,28.334291357162826 41.877123516783655,17.47086198383573 40.35854475076158,12.655118166047592 47.44667197521409))')&$top=20").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 0001013d-2221-4c09-ac51-a2e46eec07d8 | PL00\_DOV\_MS\_L3A\_20180810T082822\_20180810T08282... | /eodata/CCM/VHR\_IMAGE\_2018/DOV\_MS\_L3A\_E1F0-COG... | {'type': 'Polygon', 'coordinates': \[\[\[23.52656... |
| --- | --- | --- | --- | --- |
| 1 | 0002c916-2843-421a-8b99-81494ccbbf64 | SW00\_OPT\_MS4\_1C\_20210925T103755\_20210925T10375... | /eodata/CCM/VHR\_IMAGE\_2021/OPT\_MS4\_1C\_07B6-COG... | {'type': 'Polygon', 'coordinates': \[\[\[17.28215... |
| 2 | 0003ffc3-d258-4dea-81b2-a156f31348c9 | SW00\_OPT\_MS4\_1C\_20210823T102425\_20210823T10242... | /eodata/CCM/VHR\_IMAGE\_2021/OPT\_MS4\_1C\_07B6/202... | {'type': 'Polygon', 'coordinates': \[\[\[20.86392... |

To search for products intersecting the specified point:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=OData.CSC.Intersects(area=geography'SRID=4326;POINT(-0.5319577002158441 28.65487836189358)') and Collection/Name eq 'SENTINEL-1'&$top=20`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=OData.CSC.Intersects\(area=geography%27SRID=4326;POINT\(-0.5319577002158441%2028.65487836189358\)%27\)%20and%20Collection/Name%20eq%20%27SENTINEL-1%27&$top=20)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=OData.CSC.Intersects(area=geography'SRID=4326;POINT(-0.5319577002158441 28.65487836189358)') and Collection/Name eq 'SENTINEL-1'&$top=20").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 00bd8925-3268-5f34-ba88-a5b8201bdc4d | S1B\_IW\_RAW\_\_0SDV\_20181216T055532\_20181216T0556... | NaN | {'type': 'Polygon', 'coordinates': \[\[\[-0.3279,... |
| --- | --- | --- | --- | --- |
| 1 | 00cca647-eaca-540d-ae9e-3696cad1b501 | S1B\_IW\_GRDH\_1SDV\_20181127T060404\_20181127T0604... | /eodata/Sentinel-1/SAR/GRD/2018/11/27/S1B\_IW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-0.50101... |
| 2 | 056d9c8a-434c-4c22-935e-7b11eca99946 | S1B\_IW\_GRDH\_1SDV\_20180502T055554\_20180502T0556... | /eodata/Sentinel-1/SAR/IW\_GRDH\_1S-COG/2018/05/... | {'type': 'Polygon', 'coordinates': \[\[\[1.417991... |

Disclaimers:

1. Polygon must start and end with the same point.
2. Coordinates must be given in **EPSG 4326**

Note

Please note that the geometry is validated using the Shapely library, and invalid geometries results in an error.

### Query by attributes

To search for products by attributes, it is necessary to build a filter with the following structure:

Attributes/OData.CSC.**ValueTypeAttribute** /any(att:att/Name eq ‘\[**Attribute.Name**\]’ and att/OData.CSC.**ValueTypeAttribute** /Value eq \[**Attribute.Value**\])

where

- ***ValueTypeAttribute*** can take the following values:
	- *DoubleAttribute*
	- *IntegerAttribute*
	- *DateTimeOffsetAttribute*
	- *StringAttribute*

Tip

To search for products by ***StringAttribute***, the filter query should be built with the following structure: *Attributes/OData.CSC.StringAttribute/any(att:att/Name eq ‘\[Attribute.Name\]’ and att/OData.CSC.StringAttribute/Value eq ‘\[Attribute.Value\]’)*

- ***\[Attribute.Name\]*** is the attribute name which can take multiple values depending on collection; acceptable values for the attribute name can be checked at the specified endpoints for each collection, as provided in [List of OData query attributes](https://documentation.dataspace.copernicus.eu/APIs/OData.html#list-of-odata-query-attributes-by-collection).
- ***eq*** before *\[Attribute.Value\]* can be substituted with le, lt, ge, gt in case of *Integer, Double* or *DateTimeOffset* Attributes
- ***\[Attribute.Value\]*** is the specific value that the user is searching for

To get Sentinel-2 products with CloudCover<40% between two dates:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-2' and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le 40.00) and ContentDate/Start gt 2022-01-01T00:00:00.000Z and ContentDate/Start lt 2022-01-03T00:00:00.000Z&$top=10`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-2%27%20and%20Attributes/OData.CSC.DoubleAttribute/any\(att:att/Name%20eq%20%27cloudCover%27%20and%20att/OData.CSC.DoubleAttribute/Value%20le%2040.00\)%20and%20ContentDate/Start%20gt%202022-01-01T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-01-03T00:00:00.000Z&$top=10)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-2%27%20and%20Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le 40.00) and ContentDate/Start gt 2022-01-01T00:00:00.000Z and ContentDate/Start lt 2022-01-03T00:00:00.000Z&$top=10").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | b7655921-29ab-5d6a-b0c6-b68b4ae1fe49 | S2B\_MSIL2A\_20220102T072309\_N0301\_R006\_T37NHC\_2... | /eodata/Sentinel-2/MSI/L2A/2022/01/02/S2B\_MSIL... | {'type': 'Polygon', 'coordinates': \[\[\[41.69700... |
| --- | --- | --- | --- | --- |
| 1 | 9ec93df8-d042-51a4-9e67-56f598b9796b | S2B\_MSIL2A\_20220101T175739\_N0301\_R141\_T12TYL\_2... | /eodata/Sentinel-2/MSI/L2A/2022/01/01/S2B\_MSIL... | {'type': 'Polygon', 'coordinates': \[\[\[-107.622... |
| 2 | e4f917fd-b6ed-57c3-8c2c-65e182b6426c | S2A\_MSIL1C\_20220101T002021\_N0301\_R059\_T57UXA\_2... | /eodata/Sentinel-2/MSI/L1C/2022/01/01/S2A\_MSIL... | {'type': 'Polygon', 'coordinates': \[\[\[161.6818... |

To get products with cloudCover< 10% and productType=S2MSI2A and ASCENDING orbitDirection between two dates:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-2' and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt 10.00) and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A') and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'orbitDirection' and att/OData.CSC.StringAttribute/Value eq 'ASCENDING') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T04:00:00.000Z&$top=10`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-2%27%20and%20Attributes/OData.CSC.DoubleAttribute/any\(att:att/Name%20eq%20%27cloudCover%27%20and%20att/OData.CSC.DoubleAttribute/Value%20lt%2010.00\)%20and%20Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27productType%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27S2MSI2A%27\)%20and%20Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27orbitDirection%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27ASCENDING%27\)%20and%20ContentDate/Start%20gt%202022-05-03T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-05-03T04:00:00.000Z&$top=10)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-2' and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt 10.00) and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A') and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'orbitDirection' and att/OData.CSC.StringAttribute/Value eq 'ASCENDING') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T04:00:00.000Z&$top=10").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 7e0f9557-d537-56bb-90a1-9b4a746f0f55 | S2B\_MSIL2A\_20220503T000139\_N0400\_R016\_T08XMQ\_2... | /eodata/Sentinel-2/MSI/L2A/2022/05/03/S2B\_MSIL... | {'type': 'Polygon', 'coordinates': \[\[\[-138.241... |
| --- | --- | --- | --- | --- |
| 1 | a3041799-63e6-5b61-a16a-cb5bfabce2aa | S2B\_MSIL2A\_20220503T000139\_N0400\_R016\_T09XVJ\_2... | /eodata/Sentinel-2/MSI/L2A/2022/05/03/S2B\_MSIL... | {'type': 'Polygon', 'coordinates': \[\[\[-128.506... |
| 2 | 716d55e7-ee2a-5985-afed-4ca073864ca9 | S2B\_MSIL2A\_20220503T000139\_N0400\_R016\_T08XNQ\_2... | /eodata/Sentinel-2/MSI/L2A/2022/05/03/S2B\_MSIL... | {'type': 'Polygon', 'coordinates': \[\[\[-135.001... |

To query a subset of CCM data for a specific area of interest and time period, selecting a specific mission, e.g. only Worldview-3:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'CCM' and OData.CSC.Intersects(area=geography'SRID=4326;POLYGON ((6.535492 50.600673, 6.535492 50.937662, 7.271576 50.937662, 7.271576 50.600673, 6.535492 50.600673))') and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'platformName' and att/OData.CSC.StringAttribute/Value eq 'WorldView-3') and ContentDate/Start gt 2022-05-20T00:00:00.000Z and ContentDate/Start lt 2022-07-21T00:00:00.000Z`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27CCM%27%20and%20OData.CSC.Intersects\(area=geography%27SRID=4326;POLYGON%20\(\(6.535492%2050.600673,%206.535492%2050.937662,%207.271576%2050.937662,%207.271576%2050.600673,%206.535492%2050.600673\)\)%27\)%20and%20Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27platformName%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27WorldView-3%27\)%20and%20ContentDate/Start%20gt%202022-05-20T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-07-21T00:00:00.000Z)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'CCM' and OData.CSC.Intersects(area=geography'SRID=4326;POLYGON ((6.535492 50.600673, 6.535492 50.937662, 7.271576 50.937662, 7.271576 50.600673, 6.535492 50.600673))') and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'platformName' and att/OData.CSC.StringAttribute/Value eq 'WorldView-3') and ContentDate/Start gt 2022-05-20T00:00:00.000Z and ContentDate/Start lt 2022-07-21T00:00:00.000Z").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 9f1020e6-be24-4675-8b1a-82ce6c27913f | EW03\_WV3\_MS4\_SO\_20220717T105040\_20220717T10504... | /eodata/CCM/VHR\_IMAGE\_2021/WV3\_MS4\_SO\_07B6/202... | {'type': 'Polygon', 'coordinates': \[\[\[6.99509,... |
| --- | --- | --- | --- | --- |
| 1 | 1aad79fa-90c6-498a-b2de-a20a34d06db8 | EW03\_WV3\_MS4\_OR\_20220717T105040\_20220717T10504... | /eodata/CCM/VHR\_IMAGE\_2021/WV3\_MS4\_OR\_07B6/202... | {'type': 'Polygon', 'coordinates': \[\[\[6.983405... |
| 2 | 84228bdc-ed58-4f78-9dfc-f10ad748ad96 | EW03\_WV3\_MS4\_OR\_20220717T105040\_20220717T10504... | /eodata/CCM/VHR\_IMAGE\_2021/WV3\_MS4\_OR\_07B6/202... | {'type': 'Polygon', 'coordinates': \[\[\[6.97417,... |

To search all products of a specific dataset under CCM (for example for the products belonging to VHR\_IMAGE\_2018):

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'datasetFull' and att/OData.CSC.StringAttribute/Value eq 'VHR_IMAGE_2018')`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27datasetFull%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27VHR_IMAGE_2018%27\))

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'datasetFull' and att/OData.CSC.StringAttribute/Value eq 'VHR_IMAGE_2018')").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 00646e04-06e0-4462-9ef4-cf3128abda61 | PH1B\_PHR\_MS\_\_2A\_20180920T141019\_20180920T14102... | /eodata/CCM/VHR\_IMAGE\_2018/PHR\_MS\_\_2A\_E1F0/201... | {'type': 'Polygon', 'coordinates': \[\[\[-52.7024... |
| --- | --- | --- | --- | --- |
| 1 | efa0f5ac-33af-45c2-adc6-04b929e2910a | SP06\_NAO\_MS4\_\_3\_20181030T133528\_20181030T13353... | /eodata/CCM/VHR\_IMAGE\_2018/NAO\_MS4\_\_3\_E1F0/201... | {'type': 'Polygon', 'coordinates': \[\[\[-52.7035... |
| 2 | 61eada6e-14e5-4cb2-a578-b44b3c7af932 | SP06\_NAO\_MS4\_\_3\_20180705T091411\_20180705T09143... | /eodata/CCM/VHR\_IMAGE\_2018/NAO\_MS4\_\_3\_E1F0-COG... | {'type': 'Polygon', 'coordinates': \[\[\[25.97452... |

#### List of OData query attributes by collection

To check acceptable attribute names for all Collections:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Attributes`](https://catalogue.dataspace.copernicus.eu/odata/v1/Attributes)

To check acceptable attribute names for Copernicus Sentinel Missions:

To check acceptable attribute names for Copernicus Contributing Missions (CCM):

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Attributes(CCM)`](https://catalogue.dataspace.copernicus.eu/odata/v1/Attributes\(CCM\))

To check acceptable attribute names for Complementary data:

## Orderby option

Orderby option can be used to order the products in an ascending (asc) or descending (desc) direction. If asc or desc is not specified, then the resources will be ordered in ascending order.

Tip

Using the orderby option will exclude potential duplicates from the search results.

To order products by ContentDate/Start in a descending direction:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'EW_GRDM_1S') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T03:00:00.000Z&$orderby=ContentDate/Start desc`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27productType%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27EW_GRDM_1S%27\)%20and%20ContentDate/Start%20gt%202022-05-03T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-05-03T03:00:00.000Z&$orderby=ContentDate/Start%20desc)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'EW_GRDM_1S') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T03:00:00.000Z&$orderby=ContentDate/Start desc").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 6928b379-4f9a-5473-a12a-7e7e4b83f776 | S1A\_EW\_GRDM\_1SSH\_20220503T024410\_20220503T0244... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_EW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-105.464... |
| --- | --- | --- | --- | --- |
| 1 | 4824ead5-b35c-5b83-80fa-71219c069e1c | S1A\_EW\_GRDM\_1SSH\_20220503T024310\_20220503T0244... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_EW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-103.097... |
| 2 | 0929f73c-902a-506b-9646-c908199bfa23 | S1A\_EW\_GRDM\_1SSH\_20220503T024206\_20220503T0243... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_EW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-97.2686... |

By default, if the orderby option is not used, the results are not ordered. If orderby option is used, additional orderby by id is also used, so that the results are fully ordered, and no products are lost while paginating through the results.

The acceptable arguments for this option: *ContentDate/Start*, *ContentDate/End, PublicationDate, ModificationDate*, in directions: *asc, desc*.

## Top option

Top option specifies the maximum number of items returned from a query.

To limit the number of results:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'EW_GRDM_1S') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T12:00:00.000Z&$top=100`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27productType%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27EW_GRDM_1S%27\)%20and%20ContentDate/Start%20gt%202022-05-03T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-05-03T12:00:00.000Z&$top=100)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'EW_GRDM_1S') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T12:00:00.000Z&$top=100").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 3b46f46b-4862-5587-89cb-9c52a9cc106a | S1A\_EW\_GRDM\_1SDH\_20220503T051020\_20220503T0511... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_EW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[34.92659... |
| --- | --- | --- | --- | --- |
| 1 | d1402094-d440-570c-9f55-07ffdd2fae19 | S1A\_EW\_GRDM\_1SDH\_20220503T064800\_20220503T0649... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_EW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[15.66478... |
| 2 | c8532dc6-3967-52b8-8ee4-ea63eb1a8ba2 | S1A\_EW\_GRDM\_1SSH\_20220503T090752\_20220503T0908... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_EW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-71.2011... |

The default value is set to 20.

The acceptable arguments for this option: *Integer <0,1000>*

## Skip option

The skip option can be used to skip a specific number of results. Exemplary application of this option would be paginating through the results, however, for performance reasons, we recommend limiting queries with small time intervals as a substitute for skipping in a more generic query.

To skip a specific number of results:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'EW_GRDM_1S') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T12:00:00.000Z&$skip=23`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27productType%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27EW_GRDM_1S%27\)%20and%20ContentDate/Start%20gt%202022-05-03T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-05-03T12:00:00.000Z&$skip=23)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'EW_GRDM_1S') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T12:00:00.000Z&$skip=23").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | a46c4820-96f4-55f7-9ee0-bb897597ad20 | S1A\_EW\_GRDM\_1SDH\_20220503T115007\_20220503T1150... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_EW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-77.5491... |
| --- | --- | --- | --- | --- |
| 1 | 5203efdf-4dd8-536a-9222-01364242bf7f | S1A\_EW\_GRDM\_1SSH\_20220503T090548\_20220503T0906... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_EW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-66.5592... |
| 2 | a63512e8-ca23-58e0-90fb-02f7b3cfbb39 | S1A\_EW\_GRDM\_1SDH\_20220503T083125\_20220503T0831... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_EW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-25.6077... |

The default value is set to 0.

Whenever a query results in more products than 20 (default top value), the API provides a nextLink at the bottom of the page:

```
"@OData.nextLink":
```

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'IW_GRDH_1S') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T12:00:00.000Z&$skip=20`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27productType%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27IW_GRDH_1S%27\)%20and%20ContentDate/Start%20gt%202022-05-03T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-05-03T12:00:00.000Z&$skip=20)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'IW_GRDH_1S') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T12:00:00.000Z&$skip=20").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 665501b5-56a4-5ba1-92ca-b62a4571afa2 | S1A\_IW\_GRDH\_1SDV\_20220503T013322\_20220503T0133... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_IW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-114.503... |
| --- | --- | --- | --- | --- |
| 1 | 63a43876-a5a3-52a1-a401-04c2bbd93faf | S1A\_IW\_GRDH\_1SDV\_20220503T013617\_20220503T0136... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_IW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-116.981... |
| 2 | dd677ca4-b6b2-509d-8820-0d14ab5f52d5 | S1A\_IW\_GRDH\_1SDV\_20220503T013646\_20220503T0137... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_IW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[-117.353... |

The acceptable arguments for this option: *Integer <0,10000>*

## Count option

The count option lets users get the exact number of products matching the query. This option is disabled by default to accelerate the query performance.

Tip

Don’t use *count* option if not necessary, it slows down the execution of the request.

To get the exact number of products for a given query:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'IW_GRDH_1S') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T12:00:00.000Z&$count=True`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27productType%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27IW_GRDH_1S%27\)%20and%20ContentDate/Start%20gt%202022-05-03T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-05-03T12:00:00.000Z&$count=True)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'IW_GRDH_1S') and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T12:00:00.000Z&$count=True").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 2af72689-8608-5d24-a7bb-a143f667dbd1 | S1A\_IW\_GRDH\_1SDV\_20220503T002004\_20220503T0020... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_IW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[91.09471... |
| --- | --- | --- | --- | --- |
| 1 | cc319b60-b419-59b6-b063-ace3facc8e72 | S1A\_IW\_GRDH\_1SDV\_20220503T002033\_20220503T0021... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_IW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[90.36774... |
| 2 | a2176410-7175-5b89-90f9-66be98f65d92 | S1A\_IW\_GRDH\_1SDV\_20220503T002641\_20220503T0027... | /eodata/Sentinel-1/SAR/GRD/2022/05/03/S1A\_IW\_G... | {'type': 'Polygon', 'coordinates': \[\[\[84.51186... |

The acceptable arguments for this option: *True, true, 1, False, false, 0*.

## Expand option

Expand option allows users to speficy the type of information they would like to see in detail.

The acceptable arguments for this option: *Attributes*, *Assets* and *Locations*.

### Expand Attributes

The expand attributes enables users to see the full metadata of each returned result.

To see the metadata of the results:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T12:00:00.000Z&$expand=Attributes`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20ContentDate/Start%20gt%202022-05-03T00:00:00.000Z%20and%20ContentDate/Start%20lt%202022-05-03T12:00:00.000Z&$expand=Attributes)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-03T12:00:00.000Z&$expand=Attributes").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 1d42f2d3-2456-485f-a93e-92f08bdd5c51 | S1A\_OPER\_AUX\_GNSSRD\_POD\_\_20220510T020122\_V2022... | /eodata/Sentinel-1/AUX/AUX\_GNSSRD/2022/05/03/S... | None |
| --- | --- | --- | --- | --- |
| 1 | 5c744d5c-c082-4a34-a181-81cde73cd25d | S1B\_OPER\_AUX\_GNSSRD\_POD\_\_20220510T023113\_V2022... | /eodata/Sentinel-1/AUX/AUX\_GNSSRD/2022/05/03/S... | None |
| 2 | 30252d61-e607-5525-be8d-aad13defd2c8 | S1A\_IW\_SLC\_\_1SDV\_20220503T002004\_20220503T0020... | /eodata/Sentinel-1/SAR/SLC/2022/05/03/S1A\_IW\_S... | {'type': 'Polygon', 'coordinates': \[\[\[91.08319... |

### Expand Assets

Expand assets allows to list additional assets of products, including quicklooks:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-3' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'SL_2_FRP___')&$expand=Assets`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-3%27%20and%20Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27productType%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27SL_2_FRP___%27\)&$expand=Assets)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-3' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'SL_2_FRP___')&$expand=Assets").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 36d4637d-d424-4d70-85d5-d209e3e0164e | S3B\_SL\_2\_FRP\_\_\_\_20201230T045236\_20201230T04543... | /eodata/Sentinel-3/SLSTR/SL\_2\_FRP\_\_\_/2020/12/3... | {'type': 'Polygon', 'coordinates': \[\[\[-108.014... |
| --- | --- | --- | --- | --- |
| 1 | dabbef2e-a7c2-4d59-a183-b89b9881010a | S3B\_SL\_2\_FRP\_\_\_\_20201231T235616\_20201231T23591... | /eodata/Sentinel-3/SLSTR/SL\_2\_FRP\_\_\_/2020/12/3... | {'type': 'Polygon', 'coordinates': \[\[\[134.188,... |
| 2 | 4377868e-b20f-4d47-a384-55795c3b5fec | S3B\_SL\_2\_FRP\_\_\_\_20201231T235316\_20201231T23561... | /eodata/Sentinel-3/SLSTR/SL\_2\_FRP\_\_\_/2020/12/3... | {'type': 'Polygon', 'coordinates': \[\[\[137.866,... |

### Expand Locations

Expand Locations allows users to see full list of available products’ forms (compressed/uncompressed) and locations from which they can be downloaded:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'IW_RAW__0S')&$orderby=ContentDate/Start desc&$top=10&$expand=Locations`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20Attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27productType%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27IW_RAW__0S%27\)&$orderby=ContentDate/Start%20desc&$top=10&$expand=Locations)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'IW_RAW__0S')&$orderby=ContentDate/Start desc&$top=10&$expand=Locations").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 3d52734a-bfd6-4193-9580-be493654ed56 | S1A\_IW\_RAW\_\_0SDV\_20250429T130854\_20250429T1309... | /eodata/Sentinel-1/SAR/IW\_RAW\_\_0S/2025/04/29/S... | {'type': 'Polygon', 'coordinates': \[\[\[69.2519,... |
| --- | --- | --- | --- | --- |
| 1 | 1911b21e-c670-4396-9e32-8342878cfb66 | S1A\_IW\_RAW\_\_0SDV\_20250429T130829\_20250429T1309... | /eodata/Sentinel-1/SAR/IW\_RAW\_\_0S/2025/04/29/S... | {'type': 'Polygon', 'coordinates': \[\[\[69.6681,... |
| 2 | 020f03d3-c5e0-47b1-b0c9-6ac0ff60eee5 | S1A\_IW\_RAW\_\_0SDV\_20250429T130804\_20250429T1308... | /eodata/Sentinel-1/SAR/IW\_RAW\_\_0S/2025/04/29/S... | {'type': 'Polygon', 'coordinates': \[\[\[70.0718,... |

The information about data storage locations and storage forms (compressed/uncompressed) are specified under expand=Locations.

To access more information, please review [Compressed products section](https://dataspace.copernicus.eu/explore-data/data-collections/sentinel-data/sentinel-1) within Sentinel-1 mission description.

### Quicklook

For example, a quicklook for product `S3A_SL_2_FRP____20200821T042815_20200821T043115_20200822T092750_0179_062_033_2340_LN2_O_NT_004.SEN3` with ID of a quicklook `f4a87522-dd81-4c40-856e-41d40510e3b6`, can be downloaded with the request:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Assets(f4a87522-dd81-4c40-856e-41d40510e3b6)/$value`](https://catalogue.dataspace.copernicus.eu/odata/v1/Assets\(f4a87522-dd81-4c40-856e-41d40510e3b6\)/$value)

Download link is also available under *DownloadLink* parameter in Assets.

## Select option

The select option allows users to limit the requested properties to a specific subset for each product, e.g. to select products’ Name and Id:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$select=Name,Id`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$select=Name,Id)

The list of property names must be separated by a comma - it can also include an extra space. The order of attributes in the response is assigned by default and does not depend on the order of attributes specified in the user’s query.

The Id parameter is provided in the response by default, even if it is not defined in the select option.

Currently, those attributes are available:

- Id
- Name
- ContentType
- ContentLength
- OriginDate
- PublicationDate
- ModificationDate
- Online
- EvictionDate
- S3Path
- Checksum
- ContentDate
- Footprint
- Geofootprint

To select all available attributes, the `*` symbol can be used instead of listing each property name individually:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$select=*`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$select=*)

## Listing product nodes

Product content can be listed by accessing the following URL patterns using Nodes:

```
https://download.dataspace.copernicus.eu/odata/v1/Products(<PRODUCT_UUID>)/Nodes
https://download.dataspace.copernicus.eu/odata/v1/Products(<PRODUCT_UUID>)/Nodes(<NODE_NAME>)/Nodes
https://download.dataspace.copernicus.eu/odata/v1/Products(<PRODUCT_UUID>)/Nodes(<NODE_NAME>)/Nodes(<NODE_NAME>)/Nodes
```

where:

\- is ID of the product obtained by search query,

\- is name of element inside product returned from previous listing response.

Only nodes that are folders can have their contents listed. Attempting to list Nodes for file results returning an empty list. The listing Nodes feature is available for both authorized and unauthorized users.

### Example nodes listing

Example URL:

```
https://download.dataspace.copernicus.eu/odata/v1/Products(db0c8ef3-8ec0-5185-a537-812dad3c58f8)/Nodes
```

Response:

```
{
   "result":[
      {
         "Id":"S2A_MSIL1C_20180927T051221_N0206_R033_T42FXL_20180927T073143.SAFE",
         "Name":"S2A_MSIL1C_20180927T051221_N0206_R033_T42FXL_20180927T073143.SAFE",
         "ContentLength":0,
         "ChildrenNumber":9,
         "Nodes":{
            "uri":"https://download.dataspace.copernicus.eu/odata/v1/Products(db0c8ef3-8ec0-5185-a537-812dad3c58f8)/Nodes(S2A_MSIL1C_20180927T051221_N0206_R033_T42FXL_20180927T073143.SAFE)/Nodes"
         }
      }
   ]
}
```

Every Listed Node has “uri” field, which lists its children.

## Product Download

For downloading products you need an authorization token as only authorized users are allowed to download data products.

To get the token you can use the following scripts:

or

Along with the Access Token, you will be returned a Refresh Token, the latter is used to generate a new Access Token without the need to specify a Username or Password; this helps to make requests less vulnerable to your credentials being exposed.

To re-generate the Access Token from the Refresh Token, it can be done with the following request:

  

Once you have your token, you require a product Id which can be found in the response of the products search: [`https://catalogue.dataspace.copernicus.eu/odata/v1/Products`](https://catalogue.dataspace.copernicus.eu/odata/v1/Products)

Finally, you can download the product using this script:

Tip

The examples below assume that the product is saved to a file with the “.zip” extension. The exceptions are Sentinel-5P products, which are served directly with the “.nc” extension.

```
curl -H "Authorization: Bearer $ACCESS_TOKEN" 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products(060882f4-0a34-5f14-8e25-6876e4470b0d)/$value' --location-trusted --output /tmp/product.zip
```

or

### Compressed Product Download

For downloading products in their native format (as zipped files) you need to proceed with the standard authorization as for [Product Download](https://documentation.dataspace.copernicus.eu/APIs/OData.html#product-download).

**Currently, users can access Sentinel-1 (RAW, GRD, SLC) data stored in native format and compressed for one month following their publication date within Data Space Catalogue.**

To access more information about compressed products, please review [Compressed products section](https://dataspace.copernicus.eu/explore-data/data-collections/sentinel-data/sentinel-1) within Sentinel-1 mission description.

The access to compressed products (stored in native format):

```
curl -H "Authorization: Bearer $ACCESS_TOKEN" 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products(002f0c9e-8a4c-465b-9e03-479475947630)/$zip' --location-trusted --output /tmp/product.zip
```

or

## OData DeletedProducts endpoint

The **DeletedProducts OData** endpoint allows users to access information about the deleted products in the Copernicus Data Space Ecosystem Catalog. This endpoint provides a convenient way to retrieve details about the products that have been deleted from the CDSE Catalog. By utilizing the supported operations and filtering options, users can efficiently access the required deleted products’ details. For the DeletedProducts OData endpoint, requests should be built the same way as for the OData Products endpoint [OData Query structure](https://documentation.dataspace.copernicus.eu/APIs/OData.html#query-structure) with the change in the endpoint URL ‘Products’ to ‘DeletedProducts’.

### Endpoint URL

The **DeletedProducts OData** endpoint can be accessed using the following URL:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts)

### Query structure

The DeletedProducts OData endpoint supports the same searching options as a standard OData Products endpoint. For more information, please go to [OData Query structure](https://documentation.dataspace.copernicus.eu/APIs/OData.html#query-structure)

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-1' and DeletionDate gt 2023-04-01T00:00:00.000Z and DeletionDate lt 2023-05-30T23:59:59.999Z&$orderby=DeletionDate&$top=20`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20DeletionDate%20gt%202023-04-01T00:00:00.000Z%20and%20DeletionDate%20lt%202023-05-30T23:59:59.999Z&$orderby=DeletionDate&$top=20)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-1' and DeletionDate gt 2023-04-01T00:00:00.000Z and DeletionDate lt 2023-05-30T23:59:59.999Z&$orderby=DeletionDate&$top=20").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 81e390c0-4f9c-4a3c-8813-5bc6d7b48aa1 | S1A\_EW\_GRDM\_1SSH\_20220225T025010\_20220225T0251... | Duplicated product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[-7... |
| --- | --- | --- | --- | --- |
| 1 | 1b797847-592f-4883-8cb0-e5fc9d875041 | S1A\_EW\_GRDM\_1SSH\_20220225T025010\_20220225T0251... | Duplicated product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[-7... |
| 2 | 90b6daea-016e-4277-9c2b-ed6e70158207 | S1B\_IW\_GRDH\_1SDV\_20180330T172340\_20180330T1724... | Corrupted product | {'type': 'Polygon', 'coordinates': \[\[\[4.086337... |

### Filter option

To search for products by properties, a filter should be built as explained [Filter option](https://documentation.dataspace.copernicus.eu/APIs/OData.html#filter-option)

The acceptable products’ properties for OData DeletedProducts endpoint are:

- *Name* - search for a specific product by its exact name
- *Id* - search for a specific product by its id
- *DeletionDate* - search by deletion date
- *DeletionCause* - search by deletion cause
- *Collection/Name* - search within a specific collection
- *OriginDate* - search by origin date
- *ContentDate/Start* and *ContentDate/End* - search by sensing date
- *Footprint* - search by geographic criteria
- *Attributes* - search by product’s attributes

#### Query by name

To search for a deleted product by its exact name:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Name eq 'S2A_MSIL1C_20210404T112111_N0500_R037_T31VEG_20230209T101305.SAFE'`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Name%20eq%20%27S2A_MSIL1C_20210404T112111_N0500_R037_T31VEG_20230209T101305.SAFE%27)

#### Query by Id

To search for a deleted product by its Id:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts(29008eb1-1a51-48a8-9aec-288b00f7debe)`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts\(29008eb1-1a51-48a8-9aec-288b00f7debe\))

#### Query by Deletion Date

To search for products deleted between two inclusive interval dates:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=DeletionDate ge 2023-04-26T00:00:00.000Z and DeletionDate le 2023-04-27T23:59:59.999Z`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=DeletionDate%20ge%202023-04-26T00:00:00.000Z%20and%20DeletionDate%20le%202023-04-27T23:59:59.999Z)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=DeletionDate ge 2023-04-26T00:00:00.000Z and DeletionDate le 2023-04-27T23:59:59.999Z").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | f1a5d39a-7600-4701-9e61-03347f63d526 | S1A\_IW\_GRDH\_1SDV\_20230224T230426\_20230224T2304... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[10... |
| --- | --- | --- | --- | --- |
| 1 | 766c1738-3eba-4865-81e0-c5c51f5e29b6 | S1A\_IW\_GRDH\_1SDV\_20230224T231156\_20230224T2312... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[99... |
| 2 | 474adc52-3a3c-4cf4-b498-47c5e5e64d27 | S1A\_IW\_GRDH\_1SDV\_20230225T000647\_20230225T0007... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[-9... |

#### Query by Deletion Cause

To search for products deleted from specific reason:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=DeletionCause eq 'Duplicated product' or DeletionCause eq 'Corrupted product'`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=DeletionCause%20eq%20%27Duplicated%20product%27%20or%20DeletionCause%20eq%20%27Corrupted%20product%27)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=DeletionCause eq 'Duplicated product' or DeletionCause eq 'Corrupted product'").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 517f7ea6-9fcc-5416-aac7-a5f6372e8dfe | S3B\_SR\_2\_LAN\_LI\_20220729T130832\_20220729T13170... | Duplicated product | {'type': 'Polygon', 'coordinates': \[\[\[93.1634,... |
| --- | --- | --- | --- | --- |
| 1 | 38cbab6a-d42b-57b4-a570-eed0b05a265f | S3A\_SR\_2\_LAN\_LI\_20220906T083654\_20220906T08394... | Duplicated product | {'type': 'Polygon', 'coordinates': \[\[\[97.8882,... |
| 2 | 4ed3e70a-6b67-57ad-bda2-c44006f5eafb | S3A\_SR\_2\_LAN\_HY\_20220630T194945\_20220630T19550... | Duplicated product | {'type': 'Polygon', 'coordinates': \[\[\[-115.59,... |

Allowed values of the `DelationCause` parameter are:

- Duplicated product
- Missing checksum
- Corrupted product
- Obsolete product or Other

#### Query by Collection of Products

To search for deleted products within a specific collection:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-2' and DeletionDate gt 2023-04-01T00:00:00.000Z and DeletionDate lt 2023-09-30T23:59:59.999Z`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name%20eq%20%27SENTINEL-2%27%20and%20DeletionDate%20gt%202023-04-01T00:00:00.000Z%20and%20DeletionDate%20lt%202023-09-30T23:59:59.999Z)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-2' and DeletionDate gt 2023-04-01T00:00:00.000Z and DeletionDate lt 2023-09-30T23:59:59.999Z").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 9d832d07-9fe9-40ec-b843-8af32eca7c6f | S2A\_MSIL2A\_20200603T002611\_N9999\_R102\_T01XDA\_2... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[71... |
| --- | --- | --- | --- | --- |
| 1 | df0b407e-768e-4567-9f54-cb50690907e3 | S2A\_MSIL1C\_20210401T010651\_N0500\_R131\_T55TDN\_2... | Corrupted product | {'type': 'Polygon', 'coordinates': \[\[\[146.2119... |
| 2 | 524ca315-7444-41b2-8e23-f3de06bc09bf | S2A\_MSIL1C\_20210401T010651\_N0500\_R131\_T55TCH\_2... | Corrupted product | {'type': 'Polygon', 'coordinates': \[\[\[145.9033... |

For available collections, please refer to [Query Collection of Products](https://documentation.dataspace.copernicus.eu/APIs/OData.html#query-collection-of-products). Also, please note that it is possible that none of the products have been deleted from the available collections.

#### Query by Sensing Date

To search for deleted products acquired between two dates:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=ContentDate/Start gt 2021-09-01T00:00:00.000Z and ContentDate/End lt 2021-09-01T00:05:00.000Z`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=ContentDate/Start%20gt%202021-09-01T00:00:00.000Z%20and%20ContentDate/End%20lt%202021-09-01T00:05:00.000Z)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=ContentDate/Start gt 2021-09-01T00:00:00.000Z and ContentDate/End lt 2021-09-01T00:05:00.000Z").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 2b01765d-7d3c-5f8b-b69f-88d121c42c8b | S1B\_IW\_GRDH\_1SDV\_20210901T000023\_20210901T0000... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[99... |
| --- | --- | --- | --- | --- |
| 1 | 053f10da-3028-5ca6-9ccc-66c8c56fa439 | S1B\_IW\_GRDH\_1SDV\_20210901T000048\_20210901T0001... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[98... |
| 2 | 73699a9d-cc42-5469-88a9-ecd0a595e0d9 | S1B\_IW\_GRDH\_1SDV\_20210901T000113\_20210901T0001... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[97... |

#### Query by Geographic Criteria

To search for deleted products intersecting the specified polygon:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=OData.CSC.Intersects(area=geography'SRID=4326;POLYGON ((-75.000244 -42.4521508418609, -75.000244 -43.4409190460844, -73.643585 -43.432873907284, -73.66513 -42.4443775132447, -75.000244 -42.4521508418609))') and ContentDate/Start gt 2021-01-01T00:00:00.000Z and ContentDate/End lt 2021-04-01T23:59:59.999Z`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=OData.CSC.Intersects\(area=geography%27SRID=4326;POLYGON%20\(\(-75.000244%20-42.4521508418609,%20-75.000244%20-43.4409190460844,%20-73.643585%20-43.432873907284,%20-73.66513%20-42.4443775132447,%20-75.000244%20-42.4521508418609\)\)%27\)%20and%20ContentDate/Start%20gt%202021-01-01T00:00:00.000Z%20and%20ContentDate/End%20lt%202021-04-01T23:59:59.999Z)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=OData.CSC.Intersects(area=geography'SRID=4326;POLYGON ((-75.000244 -42.4521508418609, -75.000244 -43.4409190460844, -73.643585 -43.432873907284, -73.66513 -42.4443775132447, -75.000244 -42.4521508418609))') and ContentDate/Start gt 2021-01-01T00:00:00.000Z and ContentDate/End lt 2021-04-01T23:59:59.999Z").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 9741a785-fe2a-462f-890c-17b8c351a74b | c\_gls\_LST\_202101010700\_GLOBE\_GEO\_V1.2.1\_nc | clms before go-live cleaning | {'type': 'Polygon', 'coordinates': \[\[\[-180.022... |
| --- | --- | --- | --- | --- |
| 1 | 6289fa11-8696-5821-a7cd-fd2a3695e5f6 | S2B\_MSIL2A\_20210106T144729\_N0214\_R139\_T18GWS\_2... | Other | {'type': 'Polygon', 'coordinates': \[\[\[-74.9832... |
| 2 | acf3d45f-c1a4-46b9-a2c2-3fd91d2b3dd2 | S2A\_MSIL2A\_20210101T144731\_N9999\_R139\_T18GWS\_2... | Reprocessed product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[-7... |

#### Query by attributes

To search for products by attributes, it is necessary to build a filter with the specified structure as defined [Query Collection of Products](https://documentation.dataspace.copernicus.eu/APIs/OData.html#query-collection-of-products).

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Attributes/OData.CSC.IntegerAttribute/any(att:att/Name eq 'orbitNumber' and att/OData.CSC.IntegerAttribute/Value eq 10844) and attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'orbitDirection' and att/OData.CSC.StringAttribute/Value eq 'ASCENDING')`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Attributes/OData.CSC.IntegerAttribute/any\(att:att/Name%20eq%20%27orbitNumber%27%20and%20att/OData.CSC.IntegerAttribute/Value%20eq%2010844\)%20and%20attributes/OData.CSC.StringAttribute/any\(att:att/Name%20eq%20%27orbitDirection%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27ASCENDING%27\))

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Attributes/OData.CSC.IntegerAttribute/any(att:att/Name eq 'orbitNumber' and att/OData.CSC.IntegerAttribute/Value eq 10844) and attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'orbitDirection' and att/OData.CSC.StringAttribute/Value eq 'ASCENDING')").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 9a595c3d-02ba-5ae4-811c-70f8ce642580 | S1B\_EW\_GRDH\_1SDH\_20180509T120906\_20180509T1210... | Corrupted product | {'type': 'Polygon', 'coordinates': \[\[\[-71.8987... |
| --- | --- | --- | --- | --- |
| 1 | f67ce5c3-65ab-5cfe-9796-c62087dfef29 | S1B\_EW\_GRDM\_1SDH\_20180509T121206\_20180509T1213... | Corrupted product | {'type': 'Polygon', 'coordinates': \[\[\[-81.6544... |
| 2 | b847c833-ceb8-5e23-a54e-c80c5d4a5be2 | S1B\_EW\_GRDM\_1SDH\_20180509T130033\_20180509T1301... | Corrupted product | {'type': 'Polygon', 'coordinates': \[\[\[96.64321... |

### Orderby option

Orderby option works the same way as explained [Orderby option](https://documentation.dataspace.copernicus.eu/APIs/OData.html#orderby-option).

Tip

Using the orderby option will exclude potential duplicates from the search results.

For OData DeletedProducts endpoint, acceptable arguments for this option are:

- *ContentDate/Start*
- *ContentDate/End*
- *DeletionDate*

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-1' and DeletionDate gt 2023-04-01T00:00:00.000Z and DeletionDate lt 2023-05-30T23:59:59.999Z&$orderby=DeletionDate desc`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20DeletionDate%20gt%202023-04-01T00:00:00.000Z%20and%20DeletionDate%20lt%202023-05-30T23:59:59.999Z&$orderby=DeletionDate%20desc)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-1' and DeletionDate gt 2023-04-01T00:00:00.000Z and DeletionDate lt 2023-05-30T23:59:59.999Z&$orderby=DeletionDate desc").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 17e63a3d-b68b-5286-9ed7-43f4260acb0a | S1A\_IW\_GRDH\_1SDV\_20210830T060853\_20210830T0609... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[1.... |
| --- | --- | --- | --- | --- |
| 1 | c59d69f3-59b3-5386-a4fc-ad8985d9ba37 | S1A\_IW\_GRDH\_1SDV\_20210829T233752\_20210829T2338... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[96... |
| 2 | c1993b21-f1a0-5d57-a192-b35250fae50c | S1A\_IW\_GRDH\_1SDV\_20210830T060418\_20210830T0604... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[6.... |

### Expand option

The expand option enables users to see the full metadata of each returned result.

The acceptable argument for this option is:

- *Attributes*

To see the metadata of the results:

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-1' and DeletionDate gt 2023-04-01T00:00:00.000Z and DeletionDate lt 2023-05-30T23:59:59.999Z&$expand=Attributes`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20DeletionDate%20gt%202023-04-01T00:00:00.000Z%20and%20DeletionDate%20lt%202023-05-30T23:59:59.999Z&$expand=Attributes)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-1' and DeletionDate gt 2023-04-01T00:00:00.000Z and DeletionDate lt 2023-05-30T23:59:59.999Z&$expand=Attributes").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 81e390c0-4f9c-4a3c-8813-5bc6d7b48aa1 | S1A\_EW\_GRDM\_1SSH\_20220225T025010\_20220225T0251... | Duplicated product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[-7... |
| --- | --- | --- | --- | --- |
| 1 | 1b797847-592f-4883-8cb0-e5fc9d875041 | S1A\_EW\_GRDM\_1SSH\_20220225T025010\_20220225T0251... | Duplicated product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[-7... |
| 2 | 90b6daea-016e-4277-9c2b-ed6e70158207 | S1B\_IW\_GRDH\_1SDV\_20180330T172340\_20180330T1724... | Corrupted product | {'type': 'Polygon', 'coordinates': \[\[\[4.086337... |

### Skip option

Skip option can be used as defined [Skip option](https://documentation.dataspace.copernicus.eu/APIs/OData.html#skip-option).

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-2' and ContentDate/Start ge 2021-04-01T00:00:00.000Z and ContentDate/Start le 2021-04-30T23:59:59.999Z&$skip=30`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name%20eq%20%27SENTINEL-2%27%20and%20ContentDate/Start%20ge%202021-04-01T00:00:00.000Z%20and%20ContentDate/Start%20le%202021-04-30T23:59:59.999Z&$skip=30)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-2' and ContentDate/Start ge 2021-04-01T00:00:00.000Z and ContentDate/Start le 2021-04-30T23:59:59.999Z&$skip=30").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 40fb185e-7dc9-4bfc-8e18-8796033514a6 | S2B\_MSIL2A\_20210401T001149\_N0500\_R059\_T08XNQ\_2... | Corrupted product | {'type': 'Polygon', 'coordinates': \[\[\[-135.001... |
| --- | --- | --- | --- | --- |
| 1 | a425a14e-7534-4e46-a384-7ffd5dab8f97 | S2B\_MSIL1C\_20210401T001149\_N0500\_R059\_T10XDR\_2... | Corrupted product | {'type': 'Polygon', 'coordinates': \[\[\[-129.378... |
| 2 | 46a3452b-bd33-4fc8-8d70-0eed66d2d486 | S2B\_MSIL1C\_20210401T001149\_N0500\_R059\_T07XEM\_2... | Corrupted product | {'type': 'Polygon', 'coordinates': \[\[\[-141.001... |

### Top option

Top option can be used as defined [Top option](https://documentation.dataspace.copernicus.eu/APIs/OData.html#top-option).

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-1' and ContentDate/Start ge 2021-09-01T00:00:00.000Z and ContentDate/Start le 2021-09-30T23:59:59.999Z&$top=40`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20ContentDate/Start%20ge%202021-09-01T00:00:00.000Z%20and%20ContentDate/Start%20le%202021-09-30T23:59:59.999Z&$top=40)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-1' and ContentDate/Start ge 2021-09-01T00:00:00.000Z and ContentDate/Start le 2021-09-30T23:59:59.999Z&$top=40").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 2b01765d-7d3c-5f8b-b69f-88d121c42c8b | S1B\_IW\_GRDH\_1SDV\_20210901T000023\_20210901T0000... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[99... |
| --- | --- | --- | --- | --- |
| 1 | 053f10da-3028-5ca6-9ccc-66c8c56fa439 | S1B\_IW\_GRDH\_1SDV\_20210901T000048\_20210901T0001... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[98... |
| 2 | 73699a9d-cc42-5469-88a9-ecd0a595e0d9 | S1B\_IW\_GRDH\_1SDV\_20210901T000113\_20210901T0001... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[97... |

### Count option

Count option can be used as defined [Count option](https://documentation.dataspace.copernicus.eu/APIs/OData.html#count-option)

[`https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-1' and DeletionDate gt 2023-04-01T00:00:00.000Z and DeletionDate lt 2023-05-30T23:59:59.999Z&$orderby=DeletionDate desc&$count=True`](https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name%20eq%20%27SENTINEL-1%27%20and%20DeletionDate%20gt%202023-04-01T00:00:00.000Z%20and%20DeletionDate%20lt%202023-05-30T23:59:59.999Z&$orderby=DeletionDate%20desc&$count=True)

Code

```python
json = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/DeletedProducts?$filter=Collection/Name eq 'SENTINEL-1' and DeletionDate gt 2023-04-01T00:00:00.000Z and DeletionDate lt 2023-05-30T23:59:59.999Z&$orderby=DeletionDate desc&$count=True").json()
df = pd.DataFrame.from_dict(json['value'])

# Print only specific columns
columns_to_print = ['Id', 'Name', 'DeletionCause', 'GeoFootprint']  
df[columns_to_print].head(3)
```

| 0 | 17e63a3d-b68b-5286-9ed7-43f4260acb0a | S1A\_IW\_GRDH\_1SDV\_20210830T060853\_20210830T0609... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[1.... |
| --- | --- | --- | --- | --- |
| 1 | c59d69f3-59b3-5386-a4fc-ad8985d9ba37 | S1A\_IW\_GRDH\_1SDV\_20210829T233752\_20210829T2338... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[96... |
| 2 | c1993b21-f1a0-5d57-a192-b35250fae50c | S1A\_IW\_GRDH\_1SDV\_20210830T060418\_20210830T0604... | Corrupted product | {'type': 'MultiPolygon', 'coordinates': \[\[\[\[6.... |