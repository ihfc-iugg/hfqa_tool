# # 2. Preparing dataframes
# ## 2.1. Convert to .csv utf-8 format

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


remove_rows,
change_type

