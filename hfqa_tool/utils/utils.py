#!/usr/bin/env python
# coding: utf-8

#     Author: Saman Firdaus Chishti   |   chishti@gfz-potsdam.de
# 
#     Start date: 22-10-2024
# 
#     
# **Description:** Wrapper functions for scripts Vocabulary_check.py and Combined_score.py

# # 1. Importing libraries

# In[1]:

import glob
import os
import pandas as pd

# # 1. Preparing dataframes
# ## 1.1. Convert to .csv utf-8 format

#     [Description]: Convert all the Heatflow database files within a folder in the usual Excel sheet format to .csv format. Which is easily compatible for the functions mentioned below.

# In[3]:


def readable(folder_path):    
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))

    for excel_file_path in excel_files:
        if excel_file_path.endswith('_vocab_check.xlsx') or excel_file_path.endswith('_scores_result.xlsx'):
            continue

        try:
            excel_file = pd.ExcelFile(excel_file_path, engine='openpyxl')
            
            data_list_sheet = excel_file.parse('data list')
            
            output_csv_file = os.path.splitext(excel_file_path)[0] + '.csv'
            
            data_list_sheet.to_csv(output_csv_file, index=False, encoding='utf-8')
            
            del data_list_sheet
            del excel_file
            
        except ValueError as e:
            print(f"Error processing {excel_file_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {excel_file_path}: {e}")


# # 4. Remove extra rows

#     [Description]: To perform computations on the entered HF entries only and skip the column labels. There are two conditions: firstly, when the first cell of the dataframe has the column label 'Obligation', the top 8 rows are considered description. Secondly, when the first cell has the column label 'Short Name', the top 2 rows are considered description. The function 'remove_rows()' below switches between these two conditions and removes the description to prepare the dataframe for operability with other functions.

# In[16]:


def remove_head(df):
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
    
def assign_columns():
    NumC = ['P1','P2','P4','P5','P6','P10','P11','C1','C4','C5','C6','C22','C23','C24','C27','C28','C29','C30','C33','C34','C37','C39','C40','C47']
    StrC = ['P7','P9','P12','P13','C3','C11','C12','C13','C14','C15','C17','C18','C19','C21','C31','C32','C35','C36','C41','C42','C43','C44','C45','C46','C48']
    DateC = ['C38']
    return NumC, StrC, DateC

def assign_values():
    B = ['[drilling]','[drilling-clustering]', '[mining]', '[tunneling]', '[indirect (gtm, cpd, etc.)]'] #, '[gtm]', '[cpd]'
    P = ['[probing (onshore/lake, river, etc.)]', '[probing (offshore/ocean)]', '[probing-clustering]']
    U = ["[other (specify in comments)]","[unspecified]","nan",""];
    return B, P, U

# ## 5.2. Safe float conversion 

# In[18]:


def safe_float_conversion(r):
    r = r.strip() 
    if r == '0':
        return 0.0    
    try:
        if r[0] == '-':
            return -float(r[1:])
        else:
            return float(r)
    except ValueError:
        return None



