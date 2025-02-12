import pypdf
import optparse

def find_all_files(filename):
    '''
    Searches for all files with a specific name in the local system.

    Parameters:
    filename (str): The name of the file to search for.

    Returns:
    list: A list of file paths found. Returns an empty list if none are found.
    '''
    home = os.path.expanduser("~")
    results = []
    for root, dirs, files in os.walk(home):
        if filename in files:
            file_path = os.path.join(root, filename)
            results.append(file_path)
    return results

def merge_pdf(pdf_file_paths, output_path):
    '''
    Merging PDF files into a single PDF.
    
    Parameters:
    pdf_file_paths (list): List of paths to the PDF files to be merged
    output_path (str): Path to save the merged output
    '''
    try:
        if isinstance(pdf_file_paths, list):
            writer = pypdf.PdfWriter()
            for pdf_file in pdf_file_paths:
                open_pdf = open(pdf_file, 'rb')
                reader = pypdf.PdfReader(open_pdf)
                
                for page in reader.pages:
                    writer.add_page(page)
            
            output_file = open(output_path, 'wb')
            writer.write(output_file)
        
            open_pdf.close()
            output_file.close()

            print(f"PDF successfully merged and saved as: {output_path}")
            return output_path
        else:
            raise Exception('pdf_file_paths must be a list')
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    list_of_files = [find_all_files('first_file.pdf')[0], find_all_files('second_file.pdf')[0]]
    merge_pdf(list_of_files, 'merged_file.pdf')