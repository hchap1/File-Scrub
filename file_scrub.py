from PIL import Image
import os, datetime, ffmpeg, shutil
from time import sleep

def get_type(filename, mode="datetime"):
    image_extensions = [".png", ".jpg", ".jpeg", ".heic"]
    video_extensions = [".mov", ".mp4"]
    for image_extension in image_extensions:
        if image_extension in filename:
            if mode == "datetime": return "image"
            else: return "photos"
    for video_extension in video_extensions:
        if video_extension in filename:
            if mode == "datetime": return "video"
            else: return "videos"
    return "other"

def get_creation_date(file_path:str):
    try:
        if os.path.exists(file_path):
            if get_type(file_path) == "image":
                with Image.open(file_path) as image:
                    if hasattr(image, "_getexif") and image._getexif():
                        exif_data = image._getexif()
                        if 36867 in exif_data:
                            return exif_data[36867].split(" ")[0]
                    else:
                        creation_timestamp = os.path.getctime(file_path)
                        creation_datetime = datetime.datetime.fromtimestamp(creation_timestamp)
                        formatted_creation_date = creation_datetime.strftime("%Y:%m:%d")
                        return formatted_creation_date
            elif get_type(file_path) == "video":
                try:
                    vid = ffmpeg.probe(file_path)
                    creation_time = vid["streams"][1]["tags"]["creation_time"]
                    year, month, day = creation_time.split("T")[0].split("-")
                    return "%s:%s:%s" % (year, month, day)
                except:
                    creation_timestamp = os.path.getctime(file_path)
                    creation_datetime = datetime.datetime.fromtimestamp(creation_timestamp)
                    formatted_creation_date = creation_datetime.strftime("%Y:%m:%d")
                    return formatted_creation_date
            else:
                creation_timestamp = os.path.getctime(file_path)
                creation_datetime = datetime.datetime.fromtimestamp(creation_timestamp)
                formatted_creation_date = creation_datetime.strftime("%Y:%m:%d")
                return formatted_creation_date
    except:
        return "?:?:?"
            
def get_unique_bytes(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as file_data:
            file_bytes = file_data.read()
            try: file_bytes = file_bytes[:100]
            except: pass
        return file_bytes
    
def list_directories(directory):
    directories = []
    contents = os.listdir(directory)
    for item in contents:
        if os.path.isdir(os.path.join(directory, item)):
            directories.append(directory + "/" + item)
    return directories

def list_files(directory):
    directories = []
    copies = []
    extras = []
    contents = os.listdir(directory)
    for item in contents:
        if not os.path.isdir(os.path.join(directory, item)):
            item, extension = item.split(".")
            item = item + "." + extension.lower()
            if "copy" in item.lower(): 
                copies.append(directory + "/" + item)
            elif "(1)" in item or "(2)" in item:
                extras.append(directory + "/" + item)
            else:
                directories.append(directory + "/" + item)
    return directories + extras + copies

def parse_directory(directory):
    done = False
    all_directories = [directory]
    to_scan = [directory]
    while not done:
        to_remove = []
        for dir_to_scan in to_scan:
            for dir in list_directories(dir_to_scan):
                all_directories.append(dir)
                to_scan.append(dir)
            to_remove.append(dir_to_scan)
        for dir in to_remove:
            to_scan.remove(dir)
        if len(to_scan) == 0:
            done = True
    to_remove = []
    for dir in all_directories:
        if len(os.listdir(dir)) - len(list_directories(dir)) == 0:
            to_remove.append(dir)
    for dir in to_remove:
        all_directories.remove(dir)
    return all_directories

def list_duplicates(directory):
    directories = parse_directory(directory)
    duplicates = []
    originals = []
    bytes_id = {}
    for dir in directories:
        for file in list_files(dir):
            unique_bytes = get_unique_bytes(file)
            is_copy = False
            copy_of = ""
            for key in bytes_id.keys():
                if bytes_id[key] == unique_bytes:
                    is_copy = True
                    copy_of = key
            if is_copy: 
                duplicates.append(file)
            else:
                bytes_id[file] = unique_bytes
                originals.append(file)
    return [duplicates, originals]

def encode_month(numeric_string):
    if numeric_string[0] == "0":
        numeric_string.strip("0")
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    return months[int(numeric_string) - 1]

def clean(name):
    true_name = name.split("/")[-1]
    d = true_name.split(".")
    name = d[0]
    extension = d[1]
    name.replace(" - Copy", "")
    name.replace("(1)", "")
    name.strip(" ")
    return "%s.%s" % (name, extension)

def mkpath(path):
    if not os.path.exists(path):
        components = path.split("/")
        known_index = 0
        known_path = ""
        for index, component in enumerate(components):
            if os.path.exists(known_path + component):
                known_path += component + "/"
        known_path = known_path.strip("/")
        known_index = len(known_path.split("/"))
        print("%s ALREADY EXISTS OUT OF %s [INDEX %s]" % (known_path, path, known_index))
        to_add = components[known_index + 1:]
        print("ADDING %s" % to_add)
        for c in to_add:
            if known_path[-1] != "/": known_path += "/"
            known_path +=  c
            print("ATTEMPTING TO ADD LAYER: %s TO PATH %s" % (c, known_path))
            os.mkdir(known_path)
    else:
        print("ALREADY EXISTS!\n")

def mkdir_recursive(dir):
    components = dir.split("/")
    branch = ""
    for component in components:
        branch += component + "/"
        if not os.path.exists(branch):
            os.mkdir(branch)

def arrange(directory, new_directory):
    duplicates, originals = list_duplicates(directory)
    print("Found [%s] duplicate files." % len(duplicates))
    sleep(2)
    print("Out of %s files, %s percent were duplicates." % (len(originals) + len(duplicates), round(len(duplicates) / (len(originals) + len(duplicates)) * 100)))
    sleep(2)
    for file in originals:
        date = get_creation_date(file)
        year, month, day = date.split(":")
        ftype = get_type(file, mode="sort")
        if ftype != "other": new_path = "%s/%s/%s/%s/" % (new_directory, year, month, ftype)
        else: new_path = "%s/other" % (new_directory)
        new_name = clean(file)
        if new_path[-1] != "/":
            new_path += "/"
        new_location = new_path + new_name
        mkdir_recursive(new_path)
        #os.rename(file, new_location)
        shutil.copy(file, new_location)
    print("DONE - PERFORMING SAFETY CHECK")
    
    new_dirs = list_directories(new_directory)
    total_files = 0
    for dir in new_dirs:
        total_files += len(list_files(dir))
    
    sleep(1)
    print("%s FILES PRESENT IN NEW LOCATION.")
    sleep(1)

    print("There were %s files originally, so %s were discarded." % (len(duplicates) + len(originals), len(duplicates) + len(originals) - total_files))
    sleep(1)
    print("HOWEVER, %s files were duplicates, so there was actually a loss of %s files." % (len(duplicates), len(originals) - (total_files)))
    sleep(1)
    print("DONE")


arrange("E:/file_scrub/photos", "E:/file_scrub/test")