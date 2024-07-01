#!/usr/bin/env python
# coding: utf-8

#     Author: Saman Firdaus Chishti   |   chishti@gfz-potsdam.de
# 
#     Start date: 29-02-2024
# 
#     
# **Description:** This set of code has been developed to check whether all the values entered in a Heatflow database adhere to a controlled vocabulary and proper structure. It generates an error message for each entry where the value entered is out of bounds and does not meet the assigned criteria. The code also enables checking the vocabulary for multiple values entered in a single column for a particular Heatflow data entry.
# This is in compliance with the paper by Fuchs et al. (2023) titled "[Quality-assurance of heat-flow data: The new structure and evaluation scheme of the IHFC Global Heat Flow Database](https://doi.org/10.1016/j.tecto.2023.229976)," published in Tectonophysics 863: 229976. Also revised for the newer release 2024.
# 
# The code is intended to be published on the GFZ website for the global scientific community to check if any Heatflow dataset adheres to the data structure described in the aforementioned scientific paper. It's a recommended prerequisite before calculating 'Quality Scores' for a given Heatflow dataset. The code for calculating 'Quality Scores' is provided in a separate document.

# ![Vocab Image](Graphics\Vocab.jpg)

# # 1. Importing libraries

# In[1]:

import pandas as pd
import numpy as np
import math
from datetime import datetime
import openpyxl
import warnings
import glob
import os
#get_ipython().run_cell_magic('time', '', 'import pandas as pd\nimport numpy as np\nimport math\nfrom datetime import datetime\nimport openpyxl\nimport warnings\nimport glob\nimport os\n')


# In[2]:


# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning, module='openpyxl')


# # 2. Preparing dataframes

# ## 2.1. Convert to .csv utf-8 format

#     [Description]: Convert all the Heatflow database files within a folder in the usual Excel sheet format to .csv format. Which is easily compatible for the functions mentioned below.

# In[3]:


def convert2UTF8csv(folder_path):    
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))

    for excel_file_path in excel_files:
        try:
            # Specify the engine explicitly
            excel_file = pd.ExcelFile(excel_file_path, engine='openpyxl')
            
            # Parse the 'data list' sheet
            data_list_sheet = excel_file.parse('data list')
            
            # Generate the output CSV file path
            output_csv_file = os.path.splitext(excel_file_path)[0] + '.csv'
            
            # Save the sheet to a CSV file with UTF-8 encoding
            data_list_sheet.to_csv(output_csv_file, index=False, encoding='utf-8')
            
            # Print a success message (optional)
            #print(f"Conversion complete. CSV file saved as: {output_csv_file}")
            
            # Clean up
            del data_list_sheet
            del excel_file
            
        except ValueError as e:
            print(f"Error processing {excel_file_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {excel_file_path}: {e}")


# ## 2.2. Extract 10K entries

#     [Disclaimer]: Only required for very large database with more than 10,000 entry.
#     
#     [Description]: To prepare segments of a large Heatflow database file, such as Global Heatflow Database 2024 release. Which has more than 90,000 Heatflow data entries. Each segment/ chunk would have 10,000 entries or rows. The segmentation helps run the program functions faster in generating results output.

# In[4]:


def extract10K(df,start):
    df_first_7_rows = df.head(7)
    df = remove_rows(df)

    df['ID'] = df['ID'].astype(float)
    end = start + 10000

    filtered_df = df[(df['ID'] >= start) & (df['ID'] <= end)]

    appended_df = pd.concat([df_first_7_rows, filtered_df], ignore_index=True)
    appended_df.to_csv(f"chunk{start}.csv")


# # 3. Controlled vocabulary
# ## 3.1. Assigning columns with similar data types to specific list

# In[5]:


NumC = ['P1','P2','P4','P5','P6','P10','P11','C4','C5','C6','C22','C23','C24','C27','C28','C29','C30','C33','C34','C37','C39','C40','C47']
StrC = ['P7','P9','P12','P13','C3','C11','C12','C13','C14','C15','C17','C18','C19','C21','C31','C32','C35','C36','C41','C42','C43','C44','C45','C46','C48']
DateC = ['C38']


# ## 3.2. Numeric value sets

#     [Description]: Assign permissible value ranges for columns that store numeric values. The Allowed range of values are taken from "Appendix A. Structure and field definitions of the IHFC Global Heat Flow Database" in the aforementioned paper. Also revised for the newer release 2024.

# In[6]:


num_data = {
    #'ID': ['P1','P2','P4','P5','P6','P10','P11','C4','C5','C6','C22','C23','C24','C27','C28','C29','C30','C33','C34','C37','C39','C40','C47'],
    'Min': [-999999.9,0,-90.00000,-180.00000,-12000,-12000,-12000,0,0,0,0,0,-9.99,-99999.99,-99999.99,-99999.99,-99999.99,0,0,0,0,0,0],
    'Max': [999999.9,999999.9,90.00000,180.00000,9000,9000,9000,19999.9,19999.9,999.9,99.99,99.99,99.99,99999.99,99999.99,99999.99,99999.99,99999,99999,999999,99.99,99.99,9999]
}


# In[7]:


ndf = pd.DataFrame(num_data, index=NumC)


# ### 3.2.1. Pivot the DataFrame: Rows become columns

# In[8]:


tndf = ndf.transpose()
tndf


# ## 3.3. String value sets

#     [Description]: Assign the nature of HF data entry extraction metod: borehole/mine or probe sensing. Also provide controlled vocabulary for columns that store string values. By controlled vocabulary it means the permissible options stored as values for a given column. It is possible to store multiple values in the same column for a particular entry. The allowed controlled vocabulary is taken from "Appendix A. Structure and field definitions of the IHFC Global Heat Flow Database" in the aforementioned paper. Also revised for the newer release 2024.

# In[9]:


B = ["[Drilling]","[Drilling-Clustering]","[Mining]","[Tunneling]"]
P = ["[Probing (onshore/lake, river, etc.)]","[Probing (offshore/ocean)]","[Probing-Clustering]"]
#U = ["[Other (specify in comments)]","[unspecified]"];
sP7 = ["[Onshore (continental)]","[Onshore (lake, river, etc.)]","[Offshore (continental)]","[Offshore (marine)]","[unspecified])"];
sP9=sC9 = ["[Yes]","[No]","[Unspecified]"];
sP12 = ["[Drilling]","[Mining]","[Tunneling]","[Probing (onshore/lake, river, etc.)]","[Probing (offshore/ocean)]","[Drilling-Clustering]","[Probing-Clustering]","[Other (specify in comments)]","[unspecified]"];
sP13 = ["[Hydrocarbon]","[Underground storage]","[Geothermal]","[Groundwater]","[Mapping]","[Research]","[Mining]","[Tunneling]","[Other (specify in comments)]","[unspecified]"];
sC3 = ["[Interval method]","[Bullard method]","[Boot-strapping method]","[Numerical inversion]","[Other (specify in coments)]","[unspecified]"];
sC11 = ["[Considered – p]","[Considered – T]","[Considered – pT]","[not considered]","[unspecified]"];
sC12 = ["[Tilt corrected]","[Drift corrected]","[not corrected]","[Corrected (specify)]","[unspecified]"];
sC13=sC14=sC15=sC16=sC17=sC18=sC19 = ["[Present and corrected]","[Present and not corrected]","[Present not significant]","[not recognized]","[unspecified]"];
sC20 = ["[Expedition/Cruise number]","[R/V Ship]","[D/V Platform]","[D/V Glomar Challenger]","[D/V JOIDES Resolution]","[Other (specify in comments)]","[unspecified]"];
sC21 = ["[Single Steel probe (Bullard)]","[Single Steel probe (Bullard) in-situ TC]","[Violin-Bow probe (Lister)]","[Outrigger probe (Von Herzen) in-situ TC, without corer]","[Outrigger probe (Haenel) in-situ TC, with corer]","[Outrigger probe (Ewing) with corer]","[Outrigger probe (Ewing) without corer]","[Outrigger probe (Lister) with corer]","[Outrigger probe (autonomous) without corer]","[Outrigger probe (autonomous) with corer]","[Submersible probe]","[Other (specify in comments)]","[unspecified]"];
sC31 = ["[LOGeq]","[LOGpert]","[cLOG]","[DTSeq]","[DTSpert]","[cDTS]","[BHT]","[cBHT]","[DST]","[cDST]","[RTDeq]","[RTDpert]","[cRTD]","[CPD]","[XEN]","[GTM]","[BSR]","[BLK]","[ODTT-PC]","[ODTT-TP]","[SUR]","[unspecified]","[Other (specify in comments)]"];
sC32 = ["[LOGeq]","[LOGpert]","[cLOG]","[DTSeq]","[DTSpert]","[cDTS]","[BHT]","[cBHT]","[DST]","[cDST]","[RTDeq]","[RTDpert]","[cRTD]","[CPD]","[XEN]","[GTM]","[BSR]","[BLK]","[ODTT-PC]","[ODTT-TP]","[unspecified]","[Other (specify in comments)]"];
sC35=sC36 = ["[Horner plot]","[Cylinder source method]","[Line source explosion method]","[Inverse numerical modelling]","[Other published correction]","[unspecified]","[not corrected]","[AAPG correction]"];  
sC41 = ["[In-situ probe]","[Core-log integration]","[Core samples]","[Cutting samples]","[Outcrop samples]","[Well-log interpretation]","[Mineral computation]","[Assumed from literature]","[other (specify)]","[unspecified]"];
sC42 = ["[Actual heat-flow location]","[Other location]","[Literature/unspecified]","[Unspecified]"];
sC43 = ["[Lab - point source]","[Lab - line source / full space]","[Lab - line source / half space]","[Lab - plane source / full space]","[Lab - plane source / half space]","[Lab - other]","[Probe - pulse technique]","[Well-log - deterministic approach]","[Well-log - empirical equation]","[Estimation - from chlorine content]","[Estimation - from water content/porosity]","[Estimation - from lithology and literature]","[Estimation - from mineral composition]","[unspecified]"];
sC44 = ["[Saturated measured in-situ]","[Recovered]","[Saturated measured]","[Saturated calculated]","[Dry measured]","[other (specify)]","[unspecified]"];
sC45 = ["[Unrecorded ambient pT conditions]","[Recorded ambient pT conditions]","[Actual in-situ (pT) conditions]","[Replicated in-situ (p)]","[Replicated in-situ (T)]","[Replicated in-situ (pT)]","[Corrected in-situ (p)]","[Corrected in-situ (T)]","[Corrected in-situ (pT)]","[unspecified]"];
sC46 = ["[T - Birch and Clark (1940)]","[T - Tikhomirov (1968)]","[T - Kutas & Gordienko (1971)]","[T - Anand et al. (1973)]","[T - Haenel & Zoth (1973)]","[T - Blesch et al. (1983)]","[T - Sekiguchi (1984)]","[T - Chapman et al. (1984)]","[T - Zoth & Haenel (1988)]","[T - Somerton (1992)]","[T - Sass et al. (1992)]","[T - Funnell et al. (1996)]","[T - Kukkonen et al. (1999)]","[T - Seipold (2001)]","[T - Vosteen & Schellschmidt (2003)]","[T - Sun et al. (2017)]","[T - Miranda et al. (2018)]","[T - Ratcliffe (1960)]","[p - Bridgman (1924)]","[p - Sibbitt (1975)]","[p - Kukkonen et al. (1999)]","[p - Seipold (2001)]","[p - Durutürk et al. (2002)]","[p - Demirci et al. (2004)]","[p - Görgülü et al. (2008)]","[p - Fuchs & Förster (2014)]","[pT - Ratcliffe (1960)]","[pT - Buntebarth (1991)]","[pT - Chapman & Furlong (1992)]","[pT - Emirov et al. (1997)]","[pT - Abdulagatov et al. (2006)]","[pT - Emirov & Ramazanova (2007)]","[pT - Abdulagatova et al. (2009)]","[pT - Ramazanova & Emirov (2010)]","[pT - Ramazanova & Emirov (2012)]","[pT - Emirov et al. (2017)]","[pT - Hyndman et al. (1974)]","[Site-specific experimental relationships]","[Other (specify in comments)]","[unspecified]"];
sC48 = ["[Random or periodic depth sampling (number)]","[Characterize formation conductivities]","[Well log interpretation]","[Computation from probe sensing]","[Other]","[unspecified]"];


#     [Description]: To avoid case-sensitivity issues in the controlled vocabulary

# In[10]:


B = [item.lower() for item in B]
P = [item.lower() for item in P]


#     [Description]: To store the controlled vocabulary in a dataframe structure

# In[11]:


str_data = {
    #'ID': ['P7','P9','P12','P13','C3','C11','C12','C13','C14','C15','C17','C18','C19','C21','C31','C32','C35','C36','C41','C42','C43','C44','C45','C46','C48'],#,C20
    'Values': [sP7,sP9,sP12,sP13,sC3,sC11,sC12,sC13,sC14,sC15,sC17,sC18,sC19,sC21,sC31,sC32,sC35,sC36,sC41,sC42,sC43,sC44,sC45,sC46,sC48],#,sC20
}


# In[12]:


sdf = pd.DataFrame(str_data, index=StrC)


# ### 3.3.1. Pivot the DataFrame: Rows become columns

# In[13]:


tsdf = sdf.transpose()
tsdf


# ## 3.4. Case sensitivity issue

#     [Description]: To avoid case-sensitivity issues in the controlled vocabulary

# In[14]:


tsdf = tsdf
for col in tsdf.columns:
    for id in tsdf.index:
        if isinstance(tsdf.loc[id, col], list):
            tsdf.loc[id, col] = [str(item).lower() for item in tsdf.loc[id, col]]
tsdf


# # 4. Remove extra rows

#     [Description]: To perform computations on the entered HF entries only and skip the column labels. There are two conditions: firstly, when the first cell of the dataframe has the column label 'Obligation', the top 8 rows are considered description. Secondly, when the first cell has the column label 'Short Name', the top 2 rows are considered description. The function 'remove_rows()' below switches between these two conditions and removes the description to prepare the dataframe for operability with other functions.

# In[15]:


def remove_rows(df):
    if df.at[0,'ID'] == 'Obligation':
        df_copy = df
        top_rows = df_copy.index[0:7]
        df_copy = df_copy.drop(df_copy.index[0:7])

        new_index_values = range(1, 1+len(df_copy))
        df_copy.index = new_index_values
        #flag = 6
        return df_copy
    elif df.at[0,'ID'] == 'Short Name':
        df_copy = df
        top_rows = df_copy.index[0:1]
        df_copy = df_copy.drop(df_copy.index[0:1])

        new_index_values = range(1, 1+len(df_copy))
        df_copy.index = new_index_values
        #flag = 1
        return df_copy
    else:
        return df


# # 5. Assigning data types to specific columns

#     [Description]: Convert all the columns to string data type. To resolve multiple values in a categorical field for an entry

# In[16]:


def change_type(df):
    df[NumC] = df[NumC].astype(str)
    df[StrC] = df[StrC].astype(str)
    df[DateC] = df[DateC].astype(str)   
    return df


# # 6. Converting string values to lower case

#     [Description]: To resolve case-sensitivity in the provided Heatflow database

# In[17]:


def toLower(df):
    for col in tsdf.columns:
        for id in df.index:
            df.loc[id, col] = (df.loc[id, col]).lower()
    return df


# # 7. Check relevance

# ## 7.1. Obligation

#     [Description]: Check for mandatory fields indicated by 'Obligation' label in HF database. And store information about the nature of data, whether its borehole or probe sensing.

# In[18]:


def obligation(df):
    m_dict = {}
    domain = {}
    for c in df:
        m_dict[c] = df.loc[0, c]
        domain[c] = df.loc[1, c]
    return m_dict, domain


# ## 7.2.  Structure relevance for the current release

# In[19]:


def relevance(folder_path):

    files = os.listdir(folder_path)


    csv_files = [file for file in files if file.endswith('.csv')]


    if csv_files:
        first_csv_file_path = os.path.join(folder_path, csv_files[0])
        df = pd.read_csv(first_csv_file_path)
        m_dict, domain = obligation(df)
    else:
        print("No CSV files found in the directory. Please run 'convert2UTF8csv(folder_path)' function")
    return m_dict, domain


# # 8. Vocabulary check

#     [Description]: Complete check of vocabulary separately for numeric, string and date type columns

# In[20]:


def vocabcheck(df,m_dict,domain):
    error_df = pd.DataFrame()
    error_msg =pd.DataFrame()
    error_msg_counter = 0

    for id in df.index:
        error_df.loc[id,'A'] = None
        error_df['A'] = error_df['A'].astype("string")
        
        if df.loc[id, 'P12'] in ['[other (specify in comments)]', '[unspecified]']:
            error_string = " P12:Quality Check is not possible!,"
        elif df.loc[id, 'P12'] == 'nan':
            error_string = " P12:Mandatory entry is empty; Quality Check is not possible!,"
        else:
            error_string = ""
        error_df.loc[id,'A'] = error_string

    for c in NumC:
        min_value = tndf.loc['Min', c]
        max_value = tndf.loc['Max', c]
        
        for id in df.index:
            error_df.loc[id,c] = None
            error_df[c] = error_df[c].astype("string")
            dfvalue = df.loc[id,c]

            while True:
                dfvalue = dfvalue.split(';')
                
                for dfvalue in dfvalue:
                    try:
                        r = dfvalue.strip()
                        if r:
                            r = float(r)
    
                        if  min_value <= r <= max_value:
                            error_string = ""
                            
                        elif math.isnan(r):
                            if (m_dict[c] == 'M') and (df.loc[id, c]) == 'nan':
                                if ('B' in domain[c] and ((df.loc[id, 'P12']) in B)):
                                    error_string = f" {c}:Mandatory entry is empty!," #set '[Unspecified]',"
                                elif ('S' in domain[c] and ((df.loc[id, 'P12']) in P)):
                                    error_string = f" {c}:Mandatory entry is empty!," #set '[Unspecified]',"
                                elif ((('B'or'S') in domain[c]) and (df.loc[id, 'P12'] in ['[other (specify in comments)]', '[unspecified]', 'nan'])):
                                    error_string = f" {c}:Mandatory entry is empty!," #set '[Unspecified]',"
                                else:
                                    error_string = ""
                            elif m_dict[c] == 'M':
                                if (df.loc[id, 'P12']) in B:
                                    if (c == 'C5') and (df.loc[id, 'C6'] is None):
                                        error_string = f" {c}:mandatory field!,"   
                                    else:
                                        error_string = ""
                                elif (df.loc[id, 'P12']) in P:
                                    if (c == 'C6') and (df.loc[id, 'C5'] is None):
                                        error_string = f" {c}:mandatory field!,"
                                    elif (c == 'C23') and ((df.loc[id, 'C31'] or df.loc[id, 'C32']) is None):
                                        error_string = f" {c}:mandatory field!,"
                                    else:
                                        error_string = ""
                                else:
                                    error_string = ""#error_string = f" {c}:P12: Mandatory entry is empty; Quality Check is not possible!,"  
                            else:
                                error_string = ""                                                                       
                        else:
                            error_string = f" {c}:range violated,"
                    except ValueError:
                            error_string = f" {c}:invalid format," 
                        
                    error_df.loc[id,c] = error_string
                    if error_string != "":
                        error_msg_counter= error_msg_counter+1

                if ';' not in dfvalue:
                    break
                else:
                    dfvalue = dfvalue[-1]
                          
    for c in StrC:
        string_values = tsdf.loc['Values', c]

        for id in df.index:
            error_df.loc[id,c] = None
            error_df[c] = error_df[c].astype("string")
            dfvalue = df.loc[id,c]

            while True:
                dfvalue = dfvalue.split(';')

                for dfvalue in dfvalue:
                    dfvalue = dfvalue.strip()

                    if dfvalue in string_values:
                        error_string = ""
        
                    elif dfvalue == 'nan':
                        if m_dict[c] == 'M':
                            if (c == 'C31' or 'C32') and (df.loc[id, 'C23'] is None):
                                error_string = f" {c}:mandatory field!,"
                            else:
                                if ('B' in domain[c] and ((df.loc[id, 'P12']) in B)):
                                    error_string = f" {c}:Mandatory entry is empty!," #set '[Unspecified]',"
                                elif ('S' in domain[c] and ((df.loc[id, 'P12']) in P)):
                                    error_string = f" {c}:Mandatory entry is empty!," #set '[Unspecified]',"
                                elif ((('B'or'S') in domain[c]) and (df.loc[id, 'P12'] in ['[other (specify in comments)]', '[unspecified]', 'nan'])):
                                    error_string = f" {c}:Mandatory entry is empty!," #set '[Unspecified]',"
                                else:
                                    error_string = "" #pass
                        else:
                            error_string = ""       
                    else:
                        error_string = f" {c}:vocabulary warning,"
        
                    error_df.loc[id,c] = error_string
                    if error_string != "":
                        error_msg_counter= error_msg_counter+1
                        
                if ';' not in dfvalue:
                    break
                else:
                    dfvalue = dfvalue[-1]
    
    # Compare the input date with January 1900
    jan_1900 = datetime(1900, 1, 1)
    for id in df.index:
        error_df.loc[id,'C38'] = None
        error_df['C38'] = error_df['C38'].astype("string")
        dfvalue = df.loc[id,'C38']

        while True:
                dfvalue = dfvalue.split(';')
                    
                for dfvalue in dfvalue:
                    dfvalue = dfvalue.strip()
                    
                    if dfvalue == '[unspecified]':
                        error_string = ""
                    elif df.loc[id, 'C38'] == 'nan':
                        if ('B' in domain[c] and ((df.loc[id, 'P12']) in B)):
                            error_string = " C38:Mandatory entry is empty!," #set '[Unspecified]',"
                        elif ('S' in domain[c] and ((df.loc[id, 'P12']) in P)):
                            error_string = " C38:Mandatory entry is empty!," #set '[Unspecified]',"
                        elif ((('B'or'S') in domain[c]) and (df.loc[id, 'P12'] in ['[other (specify in comments)]', '[unspecified]', 'nan'])):
                            error_string = f" {c}:Mandatory entry is empty!," #set '[Unspecified]',"
                        else:
                            error_string = "" #pass
                    else:                        
                        try:
                            if dfvalue[-2:] == "99":
                                year = int(dfvalue[:4])
                                input_date = datetime(year, 1, 1)
                            else:
                                input_date = datetime.strptime(dfvalue, '%Y-%m')
                            
                            if input_date.month == 1 and input_date.year >= jan_1900.year:
                                error_string = ""
                            elif input_date >= jan_1900:
                                error_string = ""
                            else:
                                error_string = " C38:range violated"
                        except ValueError:
                            error_string = f" C38:invalid format,"
                    if error_string != "":
                            error_msg_counter= error_msg_counter+1
            
                    error_df.loc[id,'C38'] = error_string
                error_df = error_df.astype("string")
                    
                if ';' not in dfvalue:
                    break
                else:
                    dfvalue = dfvalue[-1]
        
    result = error_df.apply(lambda x: ''.join(x), axis=1)
    result = result.astype("string")
    
    error_msg['Error'] = result

    return error_msg


# # 9. Complete check

#     [Description]: Calling previous functions to prepare data and perform vocabulary checking

# In[21]:


def Complete_check(df):
    m_dict, domain = obligation(df)
    result = vocabcheck(toLower(change_type(remove_rows(df))), m_dict, domain)
    return result


# # 10. Attach to original data

#     [Description]: Attaching the combined results column to the original database with correct indexing.

# In[22]:


def attachOG(og):
    result = Complete_check(og)
    if og.at[0, 'ID'] == 'Obligation':

        result.index = result.index + 6
    elif og.at[0, 'ID'] == 'Short Name':

        result.index = result.index + 1
    
    og = pd.merge(og, result[['Error']], left_index=True, right_index=True, how='left')
    
    return og


# # 11. Result

# ## 11.1 Results of all files in a folder

#     [Description]: To generate results for all the Heatflow database in a folder stored in .csv format 

# In[23]:


def folder_result(folder_path):

    csv_files = glob.glob(os.path.join(folder_path, '*.csv'))
    

    for csv_file_path in csv_files:

        df = pd.read_csv(csv_file_path)
        df_result = attachOG(df)

        if df_result['Error'].eq('').all():
            print("There is no error. Data is ready for Quality Check!")
        else:
            output_excel_file = os.path.splitext(csv_file_path)[0] + '_vocab_check.xlsx'        
            df_result.to_excel(output_excel_file, index=False)
            print(f"Result exported. Excel file saved as: {output_excel_file}")

    for csv_file_path in csv_files:
        os.remove(csv_file_path)


# # 12. hfqa_tool function

#      [Description]: To check the vocabulary for all the HF dataframe files in a folder.

#      [Desclaimer]: When a new data release occurs and the relevancy (indicated by 'Obligation') of a column in the HF data structure is updated, ensure that you place the data structure files with the updated column relevancy into separate folders before running the code!!

# In[24]:


def check_vocabulary():
    folder_path = input("Please enter the file directory for checking vocabulary: ")
    convert2UTF8csv(folder_path)
    folder_result(folder_path)


# In[ ]:


check_vocabulary()

