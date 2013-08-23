#!/usr/bin/python

import sys
import os
import shutil
import hashlib
import time
import glob
from PIL import Image
import commands

libreoffice='/media/pierre-eric/309451c6-b1c2-4554-99a1-30452150b211/libreoffice-master/install/program/soffice'

im_command='convert -density 150 {} -background white -alpha Background -alpha off {}'
compare_command='compare -metric NCC  {} {} null'
resize_command='convert -resize {}x{} {} {}'

def print_to_pdf_from_word(filename, output_folder):
    print ("##############################################")
    print (" print_to_pdf_from_word: '%s'" % filename)

    # Build command (using implicitely joined strings)
    # SaveAsPDF2 is a macro saving the document to ~/PDF/eee.pdf
    command = ('wine "/home/pierre-eric/.wine/drive_c/Program Files (x86)/Microsoft Office/Office12/WINWORD.EXE" '
            '/q /t "z:' + filename +
            '" /mSaveAsPDF2 /mFileExit')

    # Execute command
    os.system(command)

    # Get filename
    fullname, ext = os.path.splitext(filename)
    basename = os.path.basename(filename).replace(ext, '.pdf')

    # Move file
    shutil.copy2("/home/pierre-eric/PDF/eee.pdf", output_folder + basename)
    os.remove("/home/pierre-eric/PDF/eee.pdf")

def print_to_pdf_from_libreoffice(filename, output_folder):
    print ("##############################################")
    print ("print_to_pdf_from_libreoffice: '%s'" % filename)

    # Build command (using implicitely joined strings)
    command = (libreoffice + ' --headless --convert-to pdf --outdir ' + output_folder + ' ' + filename)

    # Execute command
    os.system(command)

def print_to_docx_from_libreoffice(filename, output_folder):
    print ("##############################################")
    print (" print_to_docx_from_libreoffice: '%s'" % filename)

    command = (libreoffice + ' --headless --convert-to docx --outdir ' + output_folder + ' ' + filename)

    # Execute command
    os.system(command)

def compare_document(absolute_path, outdir):
    try:
        with open(absolute_path): pass
    except IOError:
        print "File '%s' doesn't exist. Aborting" % absolute_path
        return -1.

    filename = os.path.basename(absolute_path)

    # First, we need a random id for this file
    file_id = hashlib.sha224(filename).hexdigest()
    full_path = outdir + file_id + '/'

    # Create folder
    if not os.path.exists(full_path):
        os.makedirs(full_path)
        os.makedirs(full_path + '/O.W')
        os.makedirs(full_path + '/O.L')
        os.makedirs(full_path + '/O.L.L')
        os.makedirs(full_path + '/O.L.O')
        
    # Copy file to folder
    shutil.copy2(absolute_path, full_path)

    if True:
        # Generate PDF from Word
        print_to_pdf_from_word(full_path + filename, full_path + '/O.W/')

        # Import in LibreOffice and print to pdf
        print_to_pdf_from_libreoffice(full_path + filename, full_path + '/O.L/')

        # Import in LibreOffice, save as docx...
        print_to_docx_from_libreoffice(full_path + filename, full_path + '/O.L/')
        # ...then reopen and print to pdf from LibreOffice
        print_to_pdf_from_libreoffice(full_path + '/O.L/' + filename, full_path + '/O.L.L/')

        # Then print to pdf from Word
        print_to_pdf_from_word(full_path + '/O.L/' + filename, full_path + '/O.L.O/')

    # Generate images from pdf
    filename_pdf = filename.replace('.docx', '.pdf')
    filename_png = filename.replace('.docx', '.png')
    for folder in ['O.W', 'O.L', 'O.L.L', 'O.L.O']:
        cmd = im_command.format(
            full_path + '/' + folder + '/' + filename_pdf,
            full_path + '/' + folder + '/' + filename_png)
        os.system(cmd)

    # Compare images
    total_scores = []
    sum_score = [0.0, 0.0, 0.0]
    single_pages = glob.glob(full_path + '/O.W/*.png')
    for single_page_png in single_pages:
        im = Image.open(single_page_png)
        width, height = im.size

        images = [single_page_png]
        # Generate all mipmaps
        while width > 10 or height > 10:
            width = int(width / 2)
            height = int(height / 2)
            name = single_page_png.replace('.png', '_' + str(width) + 'x' + str(height) + '.png')
            os.system(resize_command.format(width, height, single_page_png, name))
            images += [name]

            for folder in ['O.L', 'O.L.L', 'O.L.O']:
                full_path = single_page_png.replace('O.W', folder)
                if not os.path.exists(full_path):
                    continue
                os.system(resize_command.format(width, height, full_path, name.replace('O.W', folder)))

        # Compare mipmap
        folders = ['O.L', 'O.L.L', 'O.L.O']
        score = [0.0, 0.0, 0.0]
        steps = 1

        for image in images:
            for i in range(0, len(folders)):
                folder = folders[i]
                image2 = image.replace('O.W', folder)

                if not os.path.exists(image2):
                    print ("%s doesn't exist" % image2)
                    continue

                result, value = commands.getstatusoutput(compare_command.format(image, image2))
                if result == 0:
                    print ("Compare: %s and %s -> %s (%f)" % (image, image2, value, min(1.0, float(value))))
                    score[i] += min(1.0, float(value)) * steps
        
            steps = steps + 1

        for i in range(0, len(folders)):
            score[i] = score[i] / sum(range(1, steps))
            sum_score[i] = sum_score[i] + score[i]

        total_scores += [score]

    for i in range(0, len(sum_score)):
        sum_score[i] = sum_score[i] / float(len(single_pages))

    print ("FINAL SCORE: " + str(sum_score))

    return file_id, sum_score, len(single_pages)

if __name__ == "__main__":
    count = len(sys.argv)
    if count > 1:
        for i in range(1, len(sys.argv)):
            compare_document (sys.argv[i], '/tmp/document_compare/')