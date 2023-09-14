import os
import zipfile
import subprocess
from pdf2image import convert_from_path

def get_file_ext(file_path: str):
    root, ext = os.path.splitext(file_path)
    return ext

def search_and_extract(zip_filepath, target_files, extract_to):
    # Ensure the target directory exists
    if not os.path.exists(extract_to):
        os.makedirs(extract_to)

    extracted_files = []

    # Open the zip file in read mode
    with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
        # Loop over the files in the zip file
        for filename in zip_ref.namelist():
            # Check the filename part after the last slash
            if os.path.basename(filename) in target_files:
                # Extract the file
                zip_ref.extract(filename, extract_to)
                print(f"File {filename} extracted to {extract_to}")
                extracted_files.append(extract_to + "/" + os.path.basename(filename))
    return extracted_files


def document_preview(document_file_path, preview_file_path):
    # Check the file extension
    if not document_file_path.endswith((".ppt", ".pptx", ".doc", ".docx")):
        raise ValueError("File must be a .ppt, .pptx, .doc, .docx file")

    # Generate a temporary pdf path
    pdf_file_path = os.path.splitext(document_file_path)[0] + ".pdf"
    print(pdf_file_path)

    # Convert PowerPoint to PDF using unoconv
    subprocess.run(["unoconv", "-f", "pdf", "-o", pdf_file_path, document_file_path])

    # Convert PDF to list of images
    images = convert_from_path(pdf_file_path)

    preview_file_paths = []
    for i, image in enumerate(images):
        fname = os.path.splitext(preview_file_path)[0] + f"-{i}.jpg"
        image.save(fname, "JPEG")
        preview_file_paths.append(fname)
    # Save the first image (the first slide of the ppt) to the preview_file_path
    # images[0].save(preview_file_path, "JPEG")

    return preview_file_paths
