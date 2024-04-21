from PIL import Image
from pillow_heif import register_heif_opener

import os, datetime, ffmpeg, shutil
from sys import argv
from time import sleep

#dependencies 
# ffmpeg
# ffprobe - also this https://stackoverflow.com/questions/57350259/filenotfounderror-errno-2-no-such-file-or-directory-ffprobe-ffprobe
# PIL
# pillow_heif

lastfile = None 
opCount = None 
total_files = 0

class lastOperation:
    def __init__(self, self_path, self_fileType, self_createDate) -> None:
        self.path = self_path
        self.fileType = self_fileType
        self.createDate = self_createDate
class fileCounter:
    def __init__(self, imageCount, videoCount, otherCount, videoLength, failures) -> None:
        self.imageCount = imageCount
        self.videoCount = videoCount
        self.otherCount = otherCount
        self.videoLength = videoLength
        self.failures = failures 

    def totalCount(self):
        totalCount = self.imageCount + self.videoCount + self.otherCount + self.failures 
        return totalCount

def get_type(filename, mode="datetime"):
    image_extensions = [".png", ".jpg", ".jpeg", ".heic"]
    video_extensions = [".mov", ".mp4"]
    file_type = None 
    for image_extension in image_extensions:
        if image_extension in filename:
            if mode == "datetime": file_type = "image"
            else:
                file_type =  "photos"
                #determine if low-res  
                with Image.open(filename) as image:
                    const_exif_image_width = 256
                    const_exif_image_height = 257
                    const_exif_photo_PixelXDimension = 40962
                    const_exif_photo_PixelYDimension = 40963
                    hasExif = hasattr(image, "getexif")
                    exif_data = image.getexif() 
                    if hasExif:
                        imgWidth = 0
                        imgHeight = 0
                        if const_exif_image_width in exif_data:
                            imgWidth = exif_data[const_exif_image_width]
                        elif const_exif_photo_PixelXDimension in exif_data:
                            imgWidth = exif_data[const_exif_image_width]
                        if const_exif_image_height in exif_data:
                            imgHeight = exif_data[const_exif_photo_PixelXDimension]
                        elif const_exif_photo_PixelYDimension in exif_data:
                            imgHeight = exif_data[const_exif_photo_PixelYDimension]

                    longestSide = imgWidth
                    if imgHeight > imgWidth:
                        longestSide = imgHeight
            
    for video_extension in video_extensions:
        if video_extension in filename:
            if mode == "datetime": file_type =  "video"
            else: file_type =  "videos"
    #fallback 
    if file_type == None: file_type = "other"
    return file_type

'''
returns the creation date for the given string, returns a null date if unable to obtain 
'''
def get_creation_date(file_path:str):
    global opCount
    formatted_creation_date = "?:?:?"
    try:
        if os.path.exists(file_path):
            fileType = get_type(file_path)
            if fileType == "image":
                global lastfile
                lastfile.fileType = "image/unknown"
                opCount.imageCount = opCount.imageCount + 1
                with Image.open(file_path) as image:
                    exifDate = None
                    const_exif_photo_date_time_original = 36867
                    const_exif_image_date_time = 306
                    hasExif = hasattr(image, "getexif")
                    exif_data = image.getexif() 
                    lastfile.fileType = 'image/' + image.format 
                    if hasExif:
                        if const_exif_photo_date_time_original in exif_data:
                            exifDate = exif_data[const_exif_photo_date_time_original]
                            formatted_creation_date = exifDate.split(" ")[0]
                        elif const_exif_image_date_time in exif_data:
                            exifDate = exif_data[const_exif_image_date_time]
                            formatted_creation_date = exifDate.split(" ")[0]

                        lastfile.createDate = formatted_creation_date + " [exif]"
                    if exifDate == None:
                        creation_timestamp = os.path.getctime(file_path)
                        creation_datetime = datetime.datetime.fromtimestamp(creation_timestamp)
                        formatted_creation_date = creation_datetime.strftime("%Y:%m:%d")
                        lastfile.createDate = formatted_creation_date + " [filedate]"

                        
            elif fileType == "video":
                lastfile.fileType = "video/unknown"
                opCount.videoCount = opCount.videoCount + 1
                try:
                    vid = ffmpeg.probe(file_path)
                    creation_time = vid["streams"][1]["tags"]["creation_time"]
                    year, month, day = creation_time.split("T")[0].split("-")
                    formatted_creation_date = "%s:%s:%s" % (year, month, day)
                    lastfile.createDate = formatted_creation_date + " [ffmpeg]"
                    try:
                        lastfile.fileType = "video" + vid["format"]["format_long_name"]
                        vid_length = vid["format"]["duration"]
                        opCount.videoLength = opCount.videoLength + float(vid_length)
                    except Exception as vMdEx:
                        if (lastfile.fileType.find("unknown") > 0):                        
                            lastfile.fileType = "video/failed"
                except Exception as e:
                    print(e)
                    creation_timestamp = os.path.getctime(file_path)
                    creation_datetime = datetime.datetime.fromtimestamp(creation_timestamp)
                    formatted_creation_date = creation_datetime.strftime("%Y:%m:%d")
                    lastfile.createDate = formatted_creation_date + " [filedate]"
            else:
                opCount.otherCount = opCount.otherCount + 1
                lastfile.fileType = "unknown"
                creation_timestamp = os.path.getctime(file_path)
                creation_datetime = datetime.datetime.fromtimestamp(creation_timestamp)
                formatted_creation_date = creation_datetime.strftime("%Y:%m:%d")
                lastfile.createDate = formatted_creation_date + " [filedate]"
    except:
        formatted_creation_date = "?:?:?"
        opCount.failures = opCount.failures + 1
        lastfile.fileType = "unknown - exception"
        lastfile.createDate = formatted_creation_date + " [exception]"
        
    return formatted_creation_date
            
def get_unique_bytes(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as file_data:
            f_bytes = None
            file_bytes = file_data.read()
            try: 
                #use first 100 and last 100 bytes of file to uniquely fingerprint
                f_bytes = file_bytes[:100]
                f_bytes += file_bytes[(len(file_bytes)-101):]
            except: pass
        return f_bytes
    
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
    global total_files 
    directories = parse_directory(directory)
    duplicates = []
    originals = []
    existing_files = {}
    for dir in directories:
        try:
            clean = 0
            dup = 0
            for file in list_files(dir):
                try: 
                    total_files += 1
                    file_bytes = get_unique_bytes(file)
                    if existing_files.get(file_bytes) == None:
                        existing_files[file_bytes] = file
                        originals.append(file)
                        clean += 1
                    else:
                        original = existing_files[file_bytes]
                        
                        print("Duplicate %s Original %s " % (file.replace(directory,"~"), original.replace(directory,"~")))
                        duplicates.append(file)
                        dup += 1
                except Exception as fileEx: 
                    print ("File Fail %s" % (file))

            print('Inspected %s ; %s original, %s duplicate' % (dir, clean, dup) )

        except Exception as pathEx:
            print ("Directory Fail %s" % (dir))
    
        
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
    global opCount 
    #init operations counter 
    opCount = fileCounter(0,0,0,0.0,0)
    global total_files 
    #register the pillow HEIF opener for .heif iOS files 
    register_heif_opener(thumbnails = False) 
    #find duplicates and originals 
    duplicates, originals = list_duplicates(directory)
    print("-------- Duplicate Check Complete ------------")
    print("Found [%s] duplicate files." % len(duplicates))
    sleep(2)
    print("Out of %s files, %s percent were duplicates." % (len(originals) + len(duplicates), round(len(duplicates) / (len(originals) + len(duplicates)) * 100)))
    sleep(2)
    print("-------- Start File Copy Operation ------------")
    copy_count = 0
    for file in originals:
        global lastfile
        lastop = "loop"
        try: 
            lastfile = lastOperation(file.replace(directory,"~"), None, None)
            #get the correct file creation date from exif/file data or file creation time
            lastop = "GetDate__"
            date = get_creation_date(file)
            lastop = "DateSplit"
            year, month, day = date.split(":")
            
            #create the path - photos are default, videos go into a subfolder, other goes elsewhere
            ftype = get_type(file, mode="sort")
            if ftype == "photos" : new_path = "%s/%s/%s/" % (new_directory, year, month)
            elif ftype != "other": new_path = "%s/%s/%s/%s/" % (new_directory, year, month, ftype)
            else: new_path = "%s/other" % (new_directory)

            #clean filename up if messy 
            lastop = "Clean____"
            new_name = clean(file)

            #get the new destination path clean and created if necessary
            if new_path[-1] != "/":
                new_path += "/"
            lastfile.newPath = new_path.replace(new_directory,"~") + new_name
            new_location = new_path + new_name
            lastop = "MkDir____"
            mkdir_recursive(new_path)
            #os.rename(file, new_location)
            
            #copy the file to the correct destination 
            lastop = "Copy_____"
            shutil.copy(file, new_location)
            copy_count += 1
            lastop = "Complete_"
        except ex as Exception:
            opCount.failures = opCount.failures + 1 
            lastop = "FAIL____"
        #log out the action 
        print('%s %s to %s; type: %s; date: %s' % (lastop, lastfile.path, lastfile.newPath, lastfile.fileType, lastfile.createDate))
            

    print("---------------- File Operation Complete -----------------")
    
    new_dirs = list_directories(new_directory)

    
    print("Image Count  : %s" % (opCount.imageCount))
    print("Video Count  : %s" % (opCount.videoCount))
    print("Other Count  : %s" % (opCount.otherCount))
    print("Fail Count   : %s" % (opCount.failures))
    print("Total Count  : %s" % (opCount.totalCount()))
    print("Video Length : %s minutes" % (opCount.videoLength / 60.0))
    
    print("Orig.  File Count: %s ; Dup File Count : %s ; Orig File Count: %s " % (total_files, len(duplicates), len(originals)))
    print("Target Copy Count: %s " % (total_files - len(duplicates)))
    sleep(1)
    print("Actual Copy Count: %s " % (copy_count))
    sleep(1)
    print("------------ Program Complete --------------")

def main(argv):
    script, first, second, third = argv
    arrange(argv[1], argv[2])
    
if __name__ == '__main__':
    if len(argv) < 4:
        argv = ['script', '/Users/bruce/downloads/Aleta iCloud/Downloaded', '/Users/bruce/downloads/Aleta iCloud/ToUpload', '3']
    main(argv)

    

