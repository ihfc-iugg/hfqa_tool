# main.py or any script where you call the functions
import hfqa_tool

def main():
    # Ask the user for the folder path once
    folder_path = input("Please enter the file directory for quality check and vocabulary check: ")

    # Call the functions with the folder path as argument
    hfqa_tool.check_vocabulary(folder_path)
    hfqa_tool.quality_score(folder_path)

if __name__ == "__main__":
    main()