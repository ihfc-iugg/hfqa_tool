#!/usr/bin/env python
# coding: utf-8

#     Author: Saman Firdaus Chishti   |   chishti@gfz-potsdam.de
# 
#     Start date: 12-08-2023
#     
# **Description:** This code has been developed to assess the quality of the Heatflow database in terms of U-score (Uncertainty quantification), M-Score (Methodological quality), and P-Flags (Perturbation effects). This is in compliance with the paper by Fuchs et al. (2023) titled "[Quality-assurance of heat-flow data: The new structure and evaluation scheme of the IHFC Global Heat Flow Database](https://doi.org/10.1016/j.tecto.2023.229976)," published in Tectonophysics 863: 229976. Also revised for the newer release 2024.
# 
# The code is intended to be published on the GFZ website for the global scientific community to use in checking the quality of any Heatflow dataset, adhering to the data structure described in the aforementioned scientific paper.

# # 1. Importing libraries

# In[1]:

import pandas as pd
import numpy as np
import math
from datetime import datetime
import glob
import os
import warnings
import time

#get_ipython().run_cell_magic('time', '', 'import pandas as pd\nimport numpy as np\nimport math\nfrom datetime import datetime\nimport glob\nimport os\nimport warnings\n')


# In[2]:


# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning, module='openpyxl')


# # 2. Convert to .csv utf-8 format

#     [Description]: To make the HF database readable and computable for the functions

# In[3]:


def convert2UTF8csv(folder_path):    
    # Get all .xlsx files in the folder
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))

    for excel_file_path in excel_files:
        # Skip files ending with '_vocab_check.xlsx'
        if excel_file_path.endswith('_vocab_check.xlsx') or excel_file_path.endswith('_scores_result.xlsx'):
            continue

        try:
            # Specify the engine explicitly
            excel_file = pd.ExcelFile(excel_file_path, engine='openpyxl')
            
            # Parse the 'data list' sheet
            data_list_sheet = excel_file.parse('data list')
            
            # Generate the output CSV file path
            output_csv_file = os.path.splitext(excel_file_path)[0] + '.csv'
            
            # Save the sheet to a CSV file with UTF-8 encoding
            data_list_sheet.to_csv(output_csv_file, index=False, encoding='utf-8')
            
            # Clean up
            del data_list_sheet
            del excel_file
            
        except ValueError as e:
            print(f"Error processing {excel_file_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {excel_file_path}: {e}")


# # 3. Remove extra rows

#     [Description]: To perform computations on the entered HF entries only and skip the column labels. There are two conditions: firstly, when the first cell of the dataframe has the column label 'Obligation', the top 8 rows are considered description. Secondly, when the first cell has the column label 'Short Name', the top 2 rows are considered description. The function 'remove_rows()' below switches between these two conditions and removes the description to prepare the dataframe for operability with other functions.

# In[4]:


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


# # 4. Assign Datatype and handle case sensitivity

# ## 4.1. Assigning columns with similar data types to specific list

# In[5]:


NumC = ['P4','P5','P6','P10','P11','C1','C2','C4','C5','C6','C22','C23','C24','C27','C28','C29','C30','C33',
        'C34','C37','C39','C40','C47']
StrC = ['P7','P9','P12','P13','C3','C11','C12','C13','C14','C15','C16','C17','C18','C19','C20','C21','C31',
        'C32','C35','C36','C41','C42','C43','C44','C45','C46','C48']
DateC = ['C38']


# ## 4.2. Check domain

#     [Description]: To check whether the type of HF data entry is of borehole/mine or probe sensing nature. Which is essential to Methodological quality evaluation (M-Score calculation)

# In[6]:


B = ['[drilling]','[drilling-clustering]', '[mining]', '[tunneling]']
P = ['[probing (onshore/lake, river, etc.)]', '[probing (offshore/ocean)]', '[probing-clustering]']


# ## 4.3. Assigning data types to specific columns

#     Description: To convert specified columns to float data type for computation and string columns to lower case to remove case-sensitivy

# In[7]:


def change_type(df):
    df1 = df

    for col in NumC:
        for index, value in df1[col].items():
            try:
                float_value = float(value)
                df1.at[index, col] = float_value
            except (ValueError, TypeError):
                df1.at[index, col] = np.nan

    df1[StrC] = df1[StrC].astype(str)
    for col in StrC:
        for id in df1.index:
            df1.loc[id, col] = (df1.loc[id, col]).lower()
    return df1


# # 5. Calculating U score

#     [Description]: Uncertainty quantification using child Heat-flow values. Determining U-Score by ranging the relative coefficient of variation (COV): estimate by numerical quantification of the heat-flow uncertainty. To avoid divide-by-zero error, such entries are masked out.

# $$
# COV(\%) = \frac{HFD_{unc}}{HFD_{mean}},
# $$
# 
# where, *HFDunc* is the uncertainty of the mean heat-flow density (*HFDmean*) defined as the arithmetic average HFD value (in mW/m2). *HFDunc* is calculated from the error propagation of the uncertainties of the conductivity (λ in W/mK) and temperature gradient ($\Delta$*T*  / $\Delta$*z* in K/m) implemented in the heat-flow calculation (Taylor, 1997):

# $$
# HFD_{unc} = \sqrt{\left( \lambda_{mean} \cdot \frac{\partial T}{\partial z_{unc}} \right)^2 + \left( \frac{\partial T}{\partial z_{mean}} \cdot \lambda_{unc} \right)^2}
# $$
# 

# In[8]:


def calc_U_score(df):
    
    HFDunc = df['C2'].abs()
    HFDmean = df['C1'].abs()

    non_zero_mask = (HFDmean != 0) & (~pd.isna(HFDmean)) & (~pd.isna(HFDunc))

    COV_prcnt = np.full_like(HFDmean, np.nan)
    COV_prcnt[non_zero_mask] = (HFDunc[non_zero_mask] / HFDmean[non_zero_mask]) * 100
    
    COV = pd.DataFrame(COV_prcnt)
    COV.columns = ['COV_percent']
    COV['U_score'] = ''
    COV['Rank'] = ''

    for id in COV.index:
        if np.isnan(COV.loc[id,'COV_percent']):
            COV.loc[id,'U_score'] = 'Ux'
            COV.loc[id,'Rank'] = 'not determined / missing data'
            
        elif COV.loc[id,'COV_percent'] < 5:
            COV.loc[id,'U_score'] = 'U1'
            COV.loc[id,'Rank'] = 'Excellent'
            
        elif 5 <= COV.loc[id,'COV_percent'] <= 15:
            COV.loc[id,'U_score'] = 'U2'
            COV.loc[id,'Rank'] = 'Good'
            
        elif 15 < COV.loc[id,'COV_percent'] <= 25:
            COV.loc[id,'U_score'] = 'U3'
            COV.loc[id,'Rank'] = 'Ok'
            
        elif COV.loc[id,'COV_percent'] > 25:
            COV.loc[id,'U_score'] = 'U4'
            COV.loc[id,'Rank'] = 'Poor'
        else:
            COV.loc[id,'U_score'] = 'Ux'
            COV.loc[id,'Rank'] = 'not determined / missing data'

    COV.index = COV.index + 1
    return COV


#     [Description]: Calling previous functions to prepare data and perform score evaluation

# In[9]:


def CompleteUscore_calc(df):
    result = calc_U_score(change_type(remove_rows(df)))
    return result


# # 6. Calculating T-Score and TC-Score

#     [Description]: The methodological quality evaluation (M-Score calculation) of Heatflow database is dependent over the product of T-score and TC-score. The temperature gradient score (T) and thermal conductivity score (TC) is quantified separately for the two different domains of heatflow data collection types (Borehole/Mine and Probing). If the information present about a Heatflow entry is not adequate for score calculation, 'Mx' for added in such scenarios. The T-score or TC-score are originally assigned as 1.0 value. From which addition or deduction are made for each case scenarios with highest penalty. In case of multiple values in a column the code enables highest penalty deduction from T-Score or TC-score.

# ## 6.1. For probe sensing:
# ### 6.1.1. Thermal gradient (T-score)

#     Description: The case-scenarios in the literature are described comprehensively for estimating the T-score for probing data, which can be found in the mentioned paper on pages 7 and 10.

# In[10]:


def ProbeT_score(df):    
    
    Pt = ['P6','C6','C23','C37']
    T_score_df = pd.DataFrame()
    T_score_df['Error_ProbeTG'] = ""
    T_score_df['X_ProbeTG'] = ""
    

    for id in df.index:
        error_string = ""
        if df.loc[id,'P12'] in P:
            T_score = 1.0
            x_present = False
            for c in Pt:
                p1=p2=p3=p4=least_penalty= None
                if c == 'P6':
                    #3) the water depth in mbsl (meters below sea level) 'P6'
                    if (abs(df.loc[id,'P6']) < 1500) or np.isnan(df.loc[id,'P6']):
                        p1 = -0.2
                    elif 2500 >= abs(df.loc[id,'P6']) >= 1500:
                        p2 = -0.1
                    elif (abs(df.loc[id,'P6']) > 2500) or ('[present and corrected]' in df.loc[id,'C17']):
                        p3 = 0                            
                    else:
                        error_string = error_string + f" {c}," 
                        x_present = True

                elif c == 'C6':
                    #1) Probe penetration depth 'C6'
                    if (df.loc[id,'C6'] < 1) or np.isnan(df.loc[id,'C6']):
                        p1 = -0.2 
                    elif 1 <= df.loc[id,'C6'] <= 3:
                        p2 = -0.1
                    elif 3 < df.loc[id,'C6'] <= 10:
                        p3 = 0
                    elif df.loc[id,'C6'] > 10:
                        p4 = 0.1
                    else:
                        error_string = error_string + f" {c},"
                        x_present = True

                elif c == 'C23':
                    #4) the tilt of the probe. 'C23'
                    if (df.loc[id,'C23'] > 30) or np.isnan(df.loc[id,'C23']):
                        p1 = -0.2 
                    elif 10 < df.loc[id,'C23'] <= 30:
                        p2 = -0.1
                    elif (0 < df.loc[id,'C23'] <= 10) or ("[tilt corrected]" in df.loc[id,'C11']):
                        p3 = 0
                    else:
                        error_string = error_string + f" {c},"
                        x_present = True

                elif c == 'C37':
                    #2) the number of temperature points used to estimate the temperature gradient 'C37'
                    if (df.loc[id,'C37'] < 1) or np.isnan(df.loc[id,'C37']):
                        p1 = -0.2 
                    elif 1 <= df.loc[id,'C37'] <= 3:
                        p2 = -0.1
                    elif 3 < df.loc[id,'C37'] <= 5:
                        p3 = 0
                    elif df.loc[id,'C37'] > 5:
                        p4 = 0.1
                    else:
                        error_string = error_string + f" {c},"
                        x_present = True

                least_penalty = min((x for x in [p1,p2,p3,p4] if x is not None), default=0)
                T_score = T_score + least_penalty

            T_score_df.loc[id,'Error_ProbeTG'] = error_string
            T_score_df.loc[id,'X_ProbeTG'] = x_present
            T_score_df.loc[id,'Probe_Tscore'] = T_score
        else:

            T_score_df.loc[id,'Error_ProbeTG'] = error_string
            T_score_df.loc[id,'Probe_Tscore'] = np.nan
    return T_score_df


#     [Description]: Calling previous functions to prepare data and perform score evaluation

# In[11]:


def Complete_PT_calc(df):
    T_score_df = ProbeT_score(change_type(remove_rows(df)))
    return T_score_df


# 
# ### 6.1.2. Thermal conductivity (TC-score)

#     Description:   The case-scenarios in the literature are described comprehensively for estimating the TC-score for probing data, that can be found in the mentioned paper at page 7 and 10.

# In[12]:


def ProbeTC_score(df):   
    
    Ptc = ['C42','C43','C45','C47']
    T_score_df = pd.DataFrame()
    T_score_df['Error_ProbeTC'] = ""
    T_score_df['X_ProbeTC'] = ""
    
    for id in df.index:
        error_string = ""
        
        if df.loc[id,'P12'] in P:
            T_score = 1.0
            x_present = False
            
            for c in Ptc:
                v = df.loc[id,c]
                p1=p2=p3=p4=least_penalty= None

                if c == 'C42': # tc_location
                    if "[literature/unspecified]" in df.loc[id,'C42']:
                        p1 = -0.2
                    elif "[other location]" in df.loc[id,'C42']:
                        p2 = -0.1
                    elif "[actual heat-flow location]" in df.loc[id,'C42']:
                        p3 = 0 
                    else:
                        error_string = error_string + f"{c}, "
                        x_present = True

                elif c == 'C43': # tc_method                    
                    if df.loc[id,'C43'].startswith('[lab'):
                        if df.loc[id,'C44'] in ["[dry measured]","[unspecified]","[other (specify)]"]:
                            p1 = -0.2
                        if "[saturated calculated]" in df.loc[id,'C44']:
                            p2 = -0.1
                        elif df.loc[id,'C44'] in ["[saturated measured]","[recovered]"]:
                            p3 = 0                              
                    elif df.loc[id,'C43'] in ["[unspecified]","[estimation - from chlorine content]",
                                              "[estimation - from water content/porosity]",
                                              "[estimation - from mineral composition]"]:
                        p1 = -0.2
                    elif "[estimation - from lithology and literature]" in df.loc[id,'C43']:
                        p2 = -0.1
                    elif "[probe - pulse technique]" in df.loc[id,'C43']:
                        p4 = 0.1
                    else:
                        error_string = error_string + f"{c}, "
                        x_present = True


                elif c == 'C45': # tc_pT_conditions
                    if df.loc[id,'C45'] in ["[recorded ambient pt conditions]","[unrecorded ambient pt conditions]",
                                            "[unspecified]"]:
                        p1 = -0.2 
                    elif df.loc[id,'C45'] in ["[replicated in-situ (p)]","[corrected in-situ (p)]",
                                              "[replicated in-situ (t)]","[corrected in-situ (t)]"]:
                        p2 = -0.1 
                    elif df.loc[id,'C45'] in ["[replicated in-situ (pt)]","[corrected in-situ (pt)]"]:
                        p3 = 0
                    elif ("[actual in-situ (pt) conditions]" in df.loc[id,'C45']) and ("[probe - pulse technique]"
                                                                                       in df.loc[id,'C43']):
                        p4 = 0.1    
                    else:
                        error_string = error_string + f"{c}, "
                        x_present = True

                elif c == 'C47': # tc_number
                    if ("[literature/unspecified]" not in df.loc[id,'C42']) and ((0<=df.loc[id,'C47']<=1)
                                                                                 or np.isnan(df.loc[id,'C47'])):
                        p1 = -0.2
                    elif ("[literature/unspecified]" not in df.loc[id,'C42']) and (2<=df.loc[id,'C47']<=3):
                        p2 = -0.1
                    elif ("[literature/unspecified]" not in df.loc[id,'C42']) and (df.loc[id,'C47']>3):
                        p3 = 0   
                    else:
                        error_string = error_string + f"{c}, "
                        x_present = True

                least_penalty = min((x for x in [p1,p2,p3,p4] if x is not None), default=0)
                T_score = T_score + least_penalty
            T_score_df.loc[id,'Error_ProbeTC'] = error_string
            T_score_df.loc[id,'X_ProbeTC'] = x_present
            T_score_df.loc[id,'Probe_TCscore'] = T_score
        else:
            T_score_df.loc[id,'Error_ProbeTC'] = error_string
            T_score_df.loc[id,'Probe_TCscore'] = np.nan
    return T_score_df


#     [Description]: Calling previous functions to prepare data and perform score evaluation

# In[13]:


def Complete_PTC_calc(df):
    T_score_df = ProbeTC_score(change_type(remove_rows(df)))
    return T_score_df


# ## 6.2. For borehole and mine data:
# ### 6.2.1. Thermal gradient (T-score)

#     [Description]:   The case-scenarios in the literature are described comprehensively for estimating the T-score for borehole/mine data, that can be found in the mentioned paper at page 7 and 11.

# In[14]:


def Bore_t_M_score(df):
    T_score_df = pd.DataFrame()
    T_score_df['Error_BoreTG'] = ""
    T_score_df['X_BoreTG'] = ""
    
    for id in df.index:
        error_string = ""
        
        if df.loc[id,'P12'] in B:
            T_score = 1.0
            x_present = False
            p1=p2=p3=least_penalty= None 
            
            if (df.loc[id,'C31'] == "[sur]") and (df.loc[id,'C32'] in ['[cpd]', '[xen]', '[gtm]', '[bsr]', '[bht]',
                                                                       '[dst]', '[rtdpert]', '[cbht]', '[cdst]',
                                                                       '[rtdeq]', '[rtdc]', '[oddt-pc]', '[oddt-tp]']):
                if df.loc[id,'C32'] in ['[cpd]', '[xen]', '[gtm]', '[bsr]'] :
                    p1 = -0.6     
                elif df.loc[id,'C32'] in ['[bht]', '[dst]', '[rtdpert]']:
                    p2 = -0.5
                elif df.loc[id,'C32'] in ['[cbht]', '[cdst]', '[rtdeq]', '[rtdc]', '[oddt-pc]', '[oddt-tp]']:
                    p3 = -0.3
                else:
                    error_string = error_string + "C32"
                    x_present = True

            elif (df.loc[id,'C37'] > 15) and ((df.loc[id,'C31'] or df.loc[id,'C32']) in ['[logpert]', '[logeq]',
                                                                                         '[clog]', '[dtseq]', '[cdts]']):
                if '[logpert]' in (df.loc[id,'C31'] or df.loc[id,'C32']):
                    p1 = -0.1
                elif (df.loc[id,'C31'] or df.loc[id,'C32']) in ['[logeq]', '[clog]', '[dtseq]', '[cdts]']:
                    p2 = 0.1
                else:
                    error_string = error_string + "C31 or C32"
                    x_present = True
                    
            elif (15 > df.loc[id,'C37'] > 2) and ((df.loc[id,'C31'] or df.loc[id,'C32']) in ['[cpd]', '[xen]', '[gtm]',
                                                                                             '[bsr]', '[logpert]', '[dtspert]',
                                                                                             '[bht]', '[dst]', '[rtdpert]',
                                                                                             '[blk]', '[logeq]', '[clog]',
                                                                                             '[dtseq]', '[cdts]', '[cbht]',
                                                                                             '[dst]', '[rtdeq]', '[rtdc]',
                                                                                             '[oddt-pc]', '[oddt-tp]']):
                if (df.loc[id,'C31'] or df.loc[id,'C32']) in ['[cpd]', '[xen]', '[gtm]', '[bsr]']:
                    p1 = -0.5
                elif (df.loc[id,'C31'] or df.loc[id,'C32']) in ['[logpert]', '[dtspert]', '[bht]', '[dst]', '[rtdpert]',
                                                                '[blk]']:
                    p2 = -0.3
                elif (df.loc[id,'C31'] or df.loc[id,'C32']) in ['[logeq]', '[clog]', '[dtseq]', '[cdts]', '[cbht]',
                                                                '[dst]', '[rtdeq]', '[rtdc]', '[oddt-pc]', '[oddt-tp]']:
                    p3 = -0.1
                else:
                    error_string = error_string + "C31 or C32"
                    x_present = True

            else:
                p1 = -0.6

            least_penalty = min((x for x in [p1,p2,p3] if x is not None), default=0)
            T_score = T_score + least_penalty
            T_score_df.loc[id,'Error_BoreTG'] = error_string
            T_score_df.loc[id,'X_BoreTG'] = x_present
            T_score_df.loc[id,'Bore_Tscore'] = T_score
        else:
            T_score_df.loc[id,'Error_BoreTG'] = error_string
            T_score_df.loc[id,'Bore_Tscore'] = np.nan
    return T_score_df


#     [Description]: Calling previous functions to prepare data and perform score evaluation

# In[15]:


def Complete_BtM_calc(df):
    T_score_df = Bore_t_M_score(change_type(remove_rows(df)))
    return T_score_df


# ### 6.2.2. Thermal conductivity

#     [Description]:   The case-scenarios in the literature are described comprehensively for estimating the TC-score for borehole/mine data, that can be found in the mentioned paper at page 7 and 11.

# In[16]:


def Bore_tc_M_score(df):
    # Assigning columns to Probe - thermal gradient
    Btc = ['C41','C42','C44','C45','C47']
    T_score_df = pd.DataFrame()
    T_score_df['Error_BoreTC'] = ""
    T_score_df['X_BoreTC'] = ""
    
    for id in df.index:
        error_string = ""
        
        if df.loc[id,'P12'] in B:
            T_score = 1.0
            x_present = False
            
            for c in Btc:
                v = df.loc[id,c]
                if isinstance(v, str) == None:
                    T_score = np.nan
                    break
                p1=p2=p3=p4=least_penalty= None
                
                if c == 'C42' and ((df.loc[id,'C4'] or df.loc[id,'C5']) is np.nan):
                #1) Localization
                    T_score = 0.1
                    break
                    
                elif (c == 'C42') and ((df.loc[id,'C4'] or df.loc[id,'C5']) is not np.nan):              
                    if "[literature/unspecified]" in df.loc[id,'C42']:
                        p1 = -0.2
                    elif "[other location]" in df.loc[id,'C42']:
                        p2 = -0.1
                    elif "[actual heat-flow location]" in df.loc[id,'C42']:
                        p3 = 0
                    else:
                        error_string = error_string + f" {c},"
                        x_present = True

                elif c == 'C41':
                # 2) Source type
                    if df.loc[id,'C41'] in ["[mineral computation]","[assumed from literature]","[other (specify)]",
                                            "[unspecified]"]:
                        p1 = -0.2
                    elif df.loc[id,'C41'] in ["[cutting samples]","[outcrop samples]","[well-log interpretation]"]:
                        p2 = -0.1
                    elif "[core samples]" in df.loc[id,'C41']:
                        p3 = 0
                    elif df.loc[id,'C41'] in ["[in-situ probe]","[core-log integration]"]:
                        p4 = 0.1
                    else:
                        error_string = error_string + f" {c},"
                        x_present = True

                elif c == 'C47':
                # 3) Number of conductivites: tc_number
                    if "[literature/unspecified]" in df.loc[id,'C42']:
                        p1 = -0.1
                    elif ("[literature/unspecified]" not in df.loc[id,'C42']) and (np.isnan(df.loc[id,'C47'])
                                                                                   or (1<=df.loc[id,'C47']<=15)):
                        p1 = -0.1
                    elif ("[literature/unspecified]" not in df.loc[id,'C42']) and (df.loc[id,'C47'] >15):
                        p2 = 0
                    else:
                        error_string = error_string + f" {c},"
                        x_present = True

                elif c == 'C44':
                    # 4) Saturation: tc_saturation
                    if df.loc[id,'C44'] in ["[dry measured]","[unspecified]","[other (specify)]"]:
                        p1 = -0.2
                    elif df.loc[id,'C44'] in ["[recovered]","[saturated calculated]"]:
                        p2 = -0.1
                    elif df.loc[id,'C44'] in ["[saturated measured in-situ]","[saturated measured]"]:
                        p3 = 0
                    else:
                        error_string = error_string + f" {c},"
                        x_present = True

                elif c == 'C45':
                    # 4) Pressure temperature: tc_pT_conditions
                    if df.loc[id,'C45'] in ["[recorded ambient pt conditions]", "[unrecorded ambient pt conditions]",
                                            "[unspecified]"]:
                        p1 = -0.2
                    elif df.loc[id,'C45'] in ["[replicated in-situ (p)]", "[corrected in-situ (p)]",
                                              "[replicated in-situ (t)]", "[corrected in-situ (t)]"]:
                        p2 = -0.1
                    elif df.loc[id,'C45'] in ["[actual in-situ (pt) conditions]", "[replicated in-situ (pt)]",
                                              "[corrected in-situ (pt)]"]:
                        p3 = 0
                    else:
                        error_string = error_string + f" {c},"
                        x_present = True
                least_penalty = min((x for x in [p1,p2,p3,p4] if x is not None), default=0)
                T_score = T_score + least_penalty
            T_score_df.loc[id,'Error_BoreTC'] = error_string
            T_score_df.loc[id,'X_BoreTC'] = x_present
            T_score_df.loc[id,'Bore_TCscore'] = T_score
        else:
            T_score_df.loc[id,'Error_BoreTC'] = error_string
            T_score_df.loc[id,'Bore_TCscore'] = np.nan
    return T_score_df


#     [Description]: Calling previous functions to prepare data and perform score evaluation

# In[17]:


def Complete_BtcM_calc(df):
    T_score_df = Bore_tc_M_score(change_type(remove_rows(df)))
    return T_score_df


# ## 6.3 Concatenate results of T scores

#     [Description]: Combining all the score results from different T and TC-score determiniation in single output df.

# In[18]:


def concatenate_TScores(df):
    new_df = change_type(remove_rows(df))
    result = pd.concat([new_df['P12'],Complete_PT_calc(df), Complete_PTC_calc(df), Complete_BtM_calc(df),
                        Complete_BtcM_calc(df)], axis=1) # 
    return result


# ## 6.4 Combine T and TC score

#     [Description]: Choosing T and TC-scores, depending on which approach: probing or borehole/mine it has been collected.

# In[19]:


def merge_Tscore(df):
    df['X_Probe'] = df['X_ProbeTG'] | df['X_ProbeTC']
    df['X_Bore'] = df['X_BoreTG'] | df['X_BoreTC']
    df['X'] = False
    df['Error'] = ''
    for id in df.index:
        #Probe_sensing
        if (df.loc[id, 'P12']) in P:
            df.loc[id, 'T_score'] = df.loc[id, 'Probe_Tscore']
            df.loc[id, 'TC_score'] = df.loc[id, 'Probe_TCscore']
            df.loc[id, 'X']= df.loc[id, 'X_Probe']
            df.loc[id, 'Error'] = df.loc[id, 'Error_ProbeTG'] + df.loc[id, 'Error_ProbeTC']
        #Borehole/ mining
        elif (df.loc[id, 'P12']) in B:
            df.loc[id, 'T_score'] = df.loc[id, 'Bore_Tscore']
            df.loc[id, 'TC_score'] = df.loc[id, 'Bore_TCscore']
            df.loc[id, 'X']= df.loc[id, 'X_Bore']
            df.loc[id, 'Error'] = df.loc[id, 'Error_BoreTG'] + df.loc[id, 'Error_BoreTC']
        else:
            pass

    column_to_remove = ['Probe_Tscore', 'Probe_TCscore', 'Bore_Tscore', 'Bore_TCscore','Error_ProbeTG',
                        'Error_ProbeTC','Error_BoreTG','Error_BoreTC','X_Probe','X_Bore','X_ProbeTG',
                        'X_ProbeTC','X_BoreTG','X_BoreTC']
    df = df.drop(column_to_remove, axis=1)
    return df


# ## 6.5 Calculate Quality

#     [Description]: Calculate the quality product of the T and TC-scores. The graphical representation of this can be found in Fig. 3 in the paper mentioned above.

# In[20]:


def T_quality(df):
    df['T_Quality'] = np.nan
    for id in df.index:
        if np.isnan(df.loc[id,'T_score']):
            df.loc[id,'T_Quality'] = df.loc[id,'TC_score']
        elif np.isnan(df.loc[id,'TC_score']):
            df.loc[id,'T_Quality'] = df.loc[id,'T_score']
        else:
            df.loc[id,'T_Quality'] = df.loc[id,'T_score'] * df.loc[id,'TC_score']        
    return df


# # 7. Calculating M Score 

#     [Description]: Determine the M-Score based on the quality assessed above. The scores range from M1 to M4, with M1 being the best quality and M4 the lowest. M-Score with a 'x' indicates inadequacy.

# ![M-Score Image](Graphics\M-score.jpg)

# In[21]:


def M_score(df):
    df['M_Score'] = ''
    for id in df.index:
        dfvalue = df.loc[id,'T_Quality']
        if 1.5000>dfvalue>=0.7500:
            if np.isnan(df.loc[id,'TC_score']) or np.isnan(df.loc[id,'T_score']) or (df.loc[id,'X']==True):
                df.loc[id,'M_Score'] = 'M1x'
            else:
                df.loc[id,'M_Score'] = 'M1'

        elif 0.7500>dfvalue>=0.5000:
            if np.isnan(df.loc[id,'TC_score']) or np.isnan(df.loc[id,'T_score']) or (df.loc[id,'X']==True):
                df.loc[id,'M_Score'] = 'M2x'
            else:
                df.loc[id,'M_Score'] = 'M2'

        elif 0.5000>dfvalue>=0.2500:
            if np.isnan(df.loc[id,'TC_score']) or np.isnan(df.loc[id,'T_score']) or (df.loc[id,'X']==True):
                df.loc[id,'M_Score'] = 'M3x'
            else:
                df.loc[id,'M_Score'] = 'M3'

        elif 0.2500>dfvalue>=0:
            if np.isnan(df.loc[id,'TC_score']) or np.isnan(df.loc[id,'T_score']) or (df.loc[id,'X']==True):
                df.loc[id,'M_Score'] = 'M4x'
            else:
                df.loc[id,'M_Score'] = 'M4'
        else:
            df.loc[id,'M_Score'] = 'Mx'
    return df


#     [Description]: Calling previous functions to prepare data and perform score evaluation

# In[22]:


def complete_MScore_calc(df):
    result = M_score(T_quality(merge_Tscore(concatenate_TScores(df))))
    return result


# # 8. Calculating P Flag

#     [Description]: The coding of perturbation effects (p-flags) is detailed in the mentioned paper on pages 8 and 9. The function 'p_flag()' checks all the relevant columns, 'C13' to 'C19' values for the same.

# ![P-flags Image](Graphics\P-flags.jpg)

# In[23]:


def p_flag(df):
    StrC = ['C13','C14','C15','C16','C17','C18','C19']
    PFlag_df = pd.DataFrame()
    PFlag_df['P_Flag'] = ""
    
    for id in df.index:
        Pflag = ''
        for c in StrC:
            # sedimentation (S/s) - C13
            if c == 'C13':                
                if '[present and corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'S'
                elif '[present and not corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'s'
                elif '[present not significant]' in df.loc[id,c]:
                    Pflag = Pflag+'X'
                elif ('[not recognised]' in df.loc[id,c]) or ('[not recognized]' in df.loc[id,c]):
                    Pflag = Pflag+'x'
                else:
                    Pflag = Pflag+'-'
            # erosion (E/e) - C14
            elif c == 'C14':                
                if '[present and corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'E'
                elif '[present and not corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'e'
                elif '[present not significant]' in df.loc[id,c]:
                    Pflag = Pflag+'X'
                elif ('[not recognised]' in df.loc[id,c]) or ('[not recognized]' in df.loc[id,c]):
                    Pflag = Pflag+'x'
                else:
                    Pflag = Pflag+'-'
            # topography/bathymetry (T/t) - C15
            elif c == 'C15':                
                if '[present and corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'T'
                elif '[present and not corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'t'
                elif '[present not significant]' in df.loc[id,c]:
                    Pflag = Pflag+'X'
                elif ('[not recognised]' in df.loc[id,c]) or ('[not recognized]' in df.loc[id,c]):
                    Pflag = Pflag+'x'
                else:
                    Pflag = Pflag+'-'
            # paleoclimate/glaciation(P/p) - C16
            elif c == 'C16':                
                if '[present and corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'P'
                elif '[present and not corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'p'
                elif '[present not significant]' in df.loc[id,c]:
                    Pflag = Pflag+'X'
                elif ('[not recognised]' in df.loc[id,c]) or ('[not recognized]' in df.loc[id,c]):
                    Pflag = Pflag+'x'
                else:
                    Pflag = Pflag+'-'
            # surface/bottom water temperature variations (V/v) - C17
            elif c == 'C17':                
                if '[present and corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'V'
                elif '[present and not corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'v'
                elif '[present not significant]' in df.loc[id,c]:
                    Pflag = Pflag+'X'
                elif ('[not recognised]' in df.loc[id,c]) or ('[not recognized]' in df.loc[id,c]):
                    Pflag = Pflag+'x'
                else:
                    Pflag = Pflag+'-'
            # convection/fluid flow/hydrate dynamics (C/c) - C18
            elif c == 'C18':                
                if '[present and corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'C'
                elif '[present and not corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'c'
                elif '[present not significant]' in df.loc[id,c]:
                    Pflag = Pflag+'X'
                elif ('[not recognised]' in df.loc[id,c]) or ('[not recognized]' in df.loc[id,c]):
                    Pflag = Pflag+'x'
                else:
                    Pflag = Pflag+'-'
            # Structural effects: heat refraction (R/r) - C19
            elif c == 'C19':                
                if '[present and corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'R'
                elif '[present and not corrected]' in df.loc[id,c]:
                    Pflag = Pflag+'r'
                elif '[present not significant]' in df.loc[id,c]:
                    Pflag = Pflag+'X'
                elif ('[not recognised]' in df.loc[id,c]) or ('[not recognized]' in df.loc[id,c]):
                    Pflag = Pflag+'x'
                else:
                    Pflag = Pflag+'-'
                    
        PFlag_df.loc[id,'P_Flag'] = Pflag
    return PFlag_df


#     [Description]: Calling previous functions to prepare data and perform score evaluation

# In[24]:


def complete_PFlag_calc(df):
    result_df = p_flag(change_type(remove_rows(df)))
    return result_df


# # 9. Combined Score

#     [Description]: Combining all the scores: U, M and P-flags together as a final output. 

# ![flowchart Image](Graphics\flowchart.jpg)

# In[25]:


def combined_score(df):
    result = pd.DataFrame()
    UScore = CompleteUscore_calc(df)
    MScore = complete_MScore_calc(df)
    Pflag = complete_PFlag_calc(df)
    result['U_score'] = UScore['U_score']
    result['M_score'] = MScore['M_Score']
    result['P_flags'] = Pflag['P_Flag']
    result['Combined_score'] = UScore['U_score'].astype(str) + MScore['M_Score'].astype(str) + '.' + Pflag['P_Flag'].astype(str)
    
    return result


# # 10. Attach to original data

#     [Description]: Attaching the combined results column to the original database with correct indexing.

# In[26]:


def attachOG(og):
    result = combined_score(og)
    

    
    if og.at[0, 'ID'] == 'Obligation':
        # Sample data for result_structure
        result_structure_data = {
            "U_score": ['-', '-', '-', 'uncertainty quantification', '-', '-', 'U-score'],
            "M_score": ['-', '-', '-', 'methodological quality', '-', '-', 'M-score'],
            "P_flags": ['-', '-', '-', 'perturbations effects', '-', '-', 'P-flags'],
            "Combined_score": ['-', '-', '-', 'quality code', '-', '-', 'Quality_Code']
        }
        result_structure = pd.DataFrame(result_structure_data)
        
        
        # Offset merge for 'Obligation' by 6 rows
        #result.index = result.index + 6
        
        # Concatenate dataframes with result_structure at the top
        result = pd.concat([result_structure, result], ignore_index=True)
        
    elif og.at[0, 'ID'] == 'Short Name':
        # Sample data for result_structure
        result_structure_data = {
            "U_score": ['U-score'],
            "M_score": ['M-score'],
            "P_flags": ['P-flags'],
            "Combined_score": ['Quality_Code']
        }
        result_structure = pd.DataFrame(result_structure_data)
        
        # Offset merge for 'Short Name' by 1 rows
        #result.index = result.index + 1
        
        # Concatenate dataframes with result_structure at the top
        result = pd.concat([result_structure, result], ignore_index=True)
    
    og = pd.merge(og, result[['Combined_score','U_score','M_score','P_flags']], left_index=True, right_index=True, how='left')
    
    # Rename multiple columns
    og.rename(columns={"Combined_score": "A9", 
                       "U_score": "A10", 
                       "M_score": "A11", 
                       "P_flags": "A12"}, inplace=True)
    
    return og


# # 11. Results

# ## 11.1. Results of all files in a folder

#     [Description]: To generate results for all the Heatflow database in a folder stored in .csv format 

# In[27]:


def folder_result(folder_path):

    csv_files = glob.glob(os.path.join(folder_path, '*.csv'))
    
    for csv_file_path in csv_files:
        df = pd.read_csv(csv_file_path)
        
        df_result = attachOG(df)
        
        output_excel_file = os.path.splitext(csv_file_path)[0] + '_scores_result.xlsx'
        
        df_result.to_excel(output_excel_file, index=False)
        
        print(f"Result exported. Excel file saved as: {output_excel_file}")

    # Delete all the .csv files after processing
    for csv_file_path in csv_files:
        os.remove(csv_file_path)
        #print(f"Deleted file: {csv_file_path}")


# # 12. hfqa_tool function

#      [Description]: To calculate Quality score for all the HF dataframe files in a folder.

# In[28]:


def quality_score():
    folder_path = input("Please enter the file/s directory for quality scores: ")
    convert2UTF8csv(folder_path)
    folder_result(folder_path)


# In[ ]:
start_time = time.time()

quality_score()

elapsed_time = time.time() - start_time
print(f"Execution time: {elapsed_time} seconds")


