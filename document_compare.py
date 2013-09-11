#!/usr/bin/python

import sys
import os
import shutil
import hashlib
import time
import glob
from PIL import Image
import commands
import tempfile

def get_libreoffice_cmd(libreoffice_base):
    return libreoffice_base + 'install/program/soffice'

im_command='pdftocairo -r 150 -png {} {}'
compare_command='compare -metric NCC  {} {} null'
resize_command='convert -resize {}x{} {} {}'

def create_folder_hierarchy_in(folder):
    os.makedirs(folder + '/O.W')
    os.makedirs(folder + '/O.L')
    os.makedirs(folder + '/O.L.L')
    os.makedirs(folder + '/O.L.O')


def print_to_pdf_from_word(filename, output_folder):
    print ("##############################################")
    print (" print_to_pdf_from_word: '%s'" % filename)

    # Build command (using implicitely joined strings)
    # SaveAsPDF2 is a macro saving the document to ~/PDF/eee.pdf
    command = ('wine "/home/pierre-eric/.wine/drive_c/Program Files (x86)/Microsoft Office/Office12/WINWORD.EXE" '
            '/q /t "z:' + filename +
            '" /mSaveAsPDF /mFileExit')

    # Execute command
    os.system(command)

    # Get filename
    fullname, ext = os.path.splitext(filename)
    basename = os.path.basename(filename).replace(ext, '.pdf')

    # Move file
    try:
        shutil.copy2("/home/pierre-eric/PDF/eee.pdf", output_folder + basename)
        os.remove("/home/pierre-eric/PDF/eee.pdf")
    except:
        print ("Word failed to open: %s" % filename)

def print_to_pdf_from_libreoffice(libreoffice, filename, output_folder):
    print ("##############################################")
    print ("print_to_pdf_from_libreoffice: '%s'" % filename)

    # Build command (using implicitely joined strings)
    command = (get_libreoffice_cmd(libreoffice) + ' --headless --convert-to pdf --outdir ' + output_folder + ' ' + filename)

    # Execute command
    os.system(command)

def print_to_format_from_libreoffice(libreoffice, format, filename, output_folder):
    print ("##############################################")
    print (" print_to %s from_libreoffice: '%s'" % (format, filename))

    command = (get_libreoffice_cmd(libreoffice) + ' --headless --convert-to ' + format[1:] + ' --outdir ' + output_folder + ' ' + filename)

    # Execute command
    os.system(command)

def compute_uid(absolute_path):
    return hashlib.md5(open(absolute_path, 'rb').read()).hexdigest()

def init_document_compare(absolute_path, outdir):
    try:
        with open(absolute_path): pass
    except IOError:
        print "File '%s' doesn't exist. Aborting" % absolute_path
        return -1.

    # First, we need a id for this file
    file_id = compute_uid(absolute_path)
    full_path = outdir + '/originals/'
    b, ext = os.path.splitext(absolute_path)

    # Copy file to folder
    shutil.copy(absolute_path, full_path + file_id + ext)

    # Generate reference pdf
    print_to_pdf_from_word(full_path + file_id + ext, full_path)

    return file_id

def generate_pdf_for_doc(filename, file_id, libreoffice, outdir):
    full_path = outdir + file_id + '/'
    b, ext = os.path.splitext(filename)

    # Create folder
    if not os.path.exists(full_path):
        os.makedirs(full_path)
        create_folder_hierarchy_in(full_path)

    # Generate PDF from Word
    #print_to_pdf_from_word(filename, full_path + '/O.W/')
    shutil.copy(filename.replace(ext, '.pdf'), full_path + '/O.W/')

    # Import in LibreOffice and print to pdf
    print_to_pdf_from_libreoffice(libreoffice, filename, full_path + '/O.L/')

    # Import in LibreOffice, save as original format
    print_to_format_from_libreoffice(libreoffice, ext, filename, full_path + '/O.L/')
    lo_generated_pdf_path = full_path + '/O.L/' + os.path.basename(filename)

    # ...then reopen and print to pdf from LibreOffice
    print_to_pdf_from_libreoffice(libreoffice, lo_generated_pdf_path, full_path + '/O.L.L/')

    # Then print to pdf from Word
    print_to_pdf_from_word(lo_generated_pdf_path, full_path + '/O.L.O/')

def generate_fullres_images_from_pdf(filename, file_id, outdir):
    full_path = outdir + file_id + '/'
    b, ext = os.path.splitext(filename)

    # Generate full resolution images from pdf
    filename_pdf = filename.replace(ext, '.pdf')
    filename_png = filename.replace(ext, '')
    for folder in ['O.W', 'O.L', 'O.L.L', 'O.L.O']:
        cmd = im_command.format(
            full_path + '/' + folder + '/' + filename_pdf,
            full_path + '/' + folder + '/' + filename_png)
        os.system(cmd)

def compare_pdf_using_images(file_id, outdir):
    full_path = outdir + file_id + '/'

    total_scores = []
    all_scores = []
    sum_score = [0.0, 0.0, 0.0]
    single_pages = glob.glob(full_path + '/O.W/*.png')
    single_pages = [f for f in single_pages if f.find('-mini.png') < 0]

    single_pages.sort()

    # Browse full resolution images (1 per page)
    for single_page_png in single_pages:
        im = Image.open(single_page_png)
        width, height = im.size

        images = [single_page_png]

        tmp_folder = tempfile.mkdtemp()
        create_folder_hierarchy_in(tmp_folder)

        mini_saved = False

        # Generate all mipmaps in temp folder
        while width > 10 or height > 10:
            width = int(width / 2)
            height = int(height / 2)
            # oooh
            base,ext = os.path.splitext(os.path.basename(single_page_png))
            name = tmp_folder + '/O.W/' + base + '_' + str(width) + 'x' + str(height) + '.png'
            # Execute IM resize command
            os.system(resize_command.format(width, height, single_page_png, name))
            # Add that to the list of images to be compared
            images += [name]

            if not mini_saved and width < 350:
                shutil.copy(name, full_path + '/O.W/{}-mini.png'.format(base))

            for folder in ['O.L', 'O.L.L', 'O.L.O']:
                # Look up corresponding image in this folder
                fp = single_page_png.replace('O.W', folder)
                if not os.path.exists(fp):
                    continue
                # If present, execute IM resize command 
                n = name.replace('O.W', folder)
                os.system(resize_command.format(width, height, fp, n))

                if not mini_saved and width < 350:
                    shutil.copy(n, full_path + '/{}/{}-mini.png'.format(folder, base))

            mini_saved = (width < 350)
        
        # Compare mipmap
        score = [0.0, 0.0, 0.0]
        folders = ['O.L', 'O.L.L', 'O.L.O']
        steps = 0
        weight = 0.0

        for image in images:
            w = 1.0 + 0.1 * steps

            # max possible score
            result, value = commands.getstatusoutput(compare_command.format(image, image))
            max_possible = min(1.0, float(value))
            print ("Max possible value: %f" % max_possible)
            for i in range(0, len(folders)):
                folder = folders[i]
                image2 = image.replace('O.W', folder)
                if not os.path.exists(image2):
                    print ("%s doesn't exist" % image2)
                    continue

                if max_possible > 0:
                    result, value = commands.getstatusoutput(compare_command.format(image, image2))
                    if result == 0:
                        print ("Compare: %s and %s -> %s (%f)" % (image, image2, value, min(1.0, float(value))))
                        score[i] += ( min(1.0, float(value)) / max_possible )* w
                else:
                    score[i] += 1.0 * w
            weight += w
            steps = steps + 1

        for i in range(0, len(folders)):
            score[i] = score[i] / weight
            sum_score[i] = sum_score[i] + score[i]
            # logs individual pages grade
            all_scores += [int(100 * score[i])]

        # remove temp dir
        shutil.rmtree(tmp_folder)

        total_scores += score

    for i in range(0, len(sum_score)):
        sum_score[i] = sum_score[i] / float(len(single_pages))

    print ("FINAL SCORE: " + str(sum_score))

    return sum_score, len(single_pages), all_scores

def get_libreoffice_sha(libreoffice):
    current = os.getcwd()
    #os.chdir(libreoffice)
    result, sha = commands.getstatusoutput("cd {} && git rev-parse --short HEAD && cd {}".format(libreoffice, current))
    #os.chdir(current)
    return sha

if __name__ == "__main__":
    count = len(sys.argv)
    if count > 1:
        outdir = '/tmp/document_compare/'
        libreoffice='/media/pierre-eric/309451c6-b1c2-4554-99a1-30452150b211/libreoffice-master-ro/'
        for i in range(1, len(sys.argv)):
            file_id = init_document_compare (sys.argv[i], outdir)
            b, ext = os.path.splitext(sys.argv[i])
            filename = file_id + ext
            generate_pdf_for_doc('/tmp/document_compare/originals/' + filename, file_id, libreoffice, outdir)
            generate_fullres_images_from_pdf(filename, file_id, outdir)
            compare_pdf_using_images(file_id, outdir)
