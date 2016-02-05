# **
# *  Copyright (C) 2015      xhaggi
# *  Copyright (C) 2012-2013 Garrett Brown
# *  Copyright (C) 2010      j48antialias
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html

from shutil import make_archive,copyfile
import os
import sys
import re
import shutil
import subprocess
import zipfile

# Compatibility with 3.0, 3.1 and 3.2 not supporting u"" literals
if sys.version < '3':
    import codecs
    def u(x):
        return codecs.unicode_escape_decode(x)[0]
else:
    def u(x):
        return x

 
class Generator:
    ADDON_WORK_DIR = "work"
    REPO_DATA_DIR = "../data"
    ADDON_XML = "../addons.xml"
    ADDON_XML_MD5 = "../addons.xml.md5"
    TEXTURE_EXTENSION = ".xbt"

    def __init__(self):
        if not os.path.exists(self.ADDON_WORK_DIR):
            os.mkdir(self.ADDON_WORK_DIR)
        self._clone_addons()
        self._generate_addons_file()
        
    def _git(self, *args):
        return subprocess.check_call(['git'] + list(args))
        
    def _texturepacker(self, input, output):
        return subprocess.check_call(['./osx/texturepacker', '-input', input, '-output', output])

    def _clone_addons(self):
        try:
            f = open("addons.txt", "r")
            for url in f.xreadlines():
                url = url.strip()
                if (url and not url.startswith("#")):
                    url_parts = url.split(" ")
                    url = url_parts[0]
                    branch = url_parts[1] if(len(url_parts) > 1) else "master"
                    repo_name = url[url.rindex("/")+1:url.rindex(".git")]
                    dir = os.path.join(self.ADDON_WORK_DIR, repo_name)

                    # logging
                    print "Update addon " + repo_name + " from " + url
                    if (os.path.isdir(dir) and os.path.isdir(os.path.join(dir, ".git"))):
                        param_worktree = "--work-tree=" + dir
                        param_gitdir = "--git-dir=" + os.path.join(dir, ".git")
                        self._git(param_worktree, param_gitdir, "fetch")
                        self._git(param_worktree, param_gitdir, "reset", "--hard", "origin/" + branch)
                    else:
                        if (branch):
                            self._git("clone", url, "--branch", branch, "--single-branch", dir)
                        else:
                            self._git("clone", url, dir)
            f.close()
        except IOError as e:
            print(e)

    def _generate_addons_file(self):
        # addon list
        addons = os.listdir(self.ADDON_WORK_DIR)
        
        # should we write the xml's
        addons_updated = False

        # final addons text
        addons_xml = u("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<addons>\n")
        # loop thru and add each addons addon.xml file
        for addon in addons:
            try:
                addondir = os.path.join(self.ADDON_WORK_DIR, addon)

                # skip any file or .svn folder or .git folder
                if (not os.path.isdir(addondir) or addon == ".svn" or addon == ".git" or addon == "nbproject" or addon == self.REPO_DATA_DIR): 
                    continue
                # create path
                _path = os.path.join(addondir, "addon.xml")
                # split lines for stripping
                xml_lines = open(_path, "r").read().splitlines()
                # new addon
                addon_xml = ""
                # loop thru cleaning each line
                for line in xml_lines:
                    # skip encoding format line
                    if (line.find("<?xml") >= 0): continue
                    # add line
                    if sys.version < '3':
                        addon_xml += unicode(line.rstrip() + "\n", "UTF-8")
                    else:
                        addon_xml += line.rstrip() + "\n"
                # we succeeded so add to our final addons.xml text
                addons_xml += addon_xml.rstrip() + "\n\n"
                # get plugin version
                fcontent = open(_path, "r").read()
                zversion = re.compile('<addon.+?version="(.+?)"', re.DOTALL).findall(fcontent)
                addonname = re.compile('<addon.+?id="(.+?)"', re.DOTALL).findall(fcontent)
                
                # logging
                print "Processing addon '" + addonname[0] + "' (version: " + zversion[0] + ")"
                
                # zip dir
                zdir = os.path.join(".", self.REPO_DATA_DIR)
                # zipped addon dir
                zaddondir = os.path.join(".", self.REPO_DATA_DIR, addonname[0])
                
                # continue next if addon already exists
                if os.path.isfile(os.path.join(zaddondir, addonname[0] + "-" + zversion[0] +".zip")):
                    print "Skipped: addon version already exist\n"
                    continue
                    
                # apply texture packer if we have a skin addon
                if (addonname[0].startswith("skin")):
                    self._apply_texture_packer(addondir)
                
                # copy changelog
                if not os.path.exists(zaddondir):
                    os.mkdir(zaddondir)
                if os.path.isfile(os.path.join(zaddondir, "changelog.txt")):
                    os.remove(os.path.join(zaddondir, "changelog.txt"))
                if os.path.isfile(os.path.join(zaddondir, "changelog-"+ zversion[0] +".txt")):
                    os.remove(os.path.join(zaddondir, "changelog-"+ zversion[0] +".txt"))
                copyfile(os.path.join(addondir, "changelog.txt"),os.path.join(zaddondir, "changelog.txt"))
                copyfile(os.path.join(addondir, "changelog.txt"),os.path.join(zaddondir, "changelog-"+ zversion[0] +".txt"))
                
                # create zipfile
                archive_name = os.path.join(zaddondir, addonname[0] +"-"+ zversion[0])
                self._make_zipfile(archive_name, addondir, addonname[0])
                
                addons_updated = True
            except Exception as e:
                # missing or poorly formatted addon.xml
                print("Excluding %s for %s" % (_path, e))
        # clean and add closing tag
        addons_xml = addons_xml.strip() + u("\n</addons>\n")
        
        if (addons_updated):
            self._save_file(addons_xml.encode("UTF-8"), file=self.ADDON_XML)        
            self._generate_md5_file()
            print("Finished updating addons xml and md5 files")

    def _apply_texture_packer(self, addon_dir):
        media_dir = os.path.join(addon_dir, "media")
        themes_dir = os.path.join(addon_dir, "themes")

        print "Apply TexturePacker to " + media_dir
        self._texturepacker(media_dir, os.path.join(media_dir, "Textures" + self.TEXTURE_EXTENSION))
        
        print "Check for for themes in " + themes_dir
        for item in os.listdir(themes_dir):
            theme_path = os.path.join(themes_dir, item)
            print "Apply TexturePacker for theme " + item
            self._texturepacker(theme_path, os.path.join(media_dir, item + self.TEXTURE_EXTENSION))
        
    def _generate_md5_file(self):
        # create a new md5 hash
        try:
            import md5
            m = md5.new(open(self.ADDON_XML, "r").read()).hexdigest()
        except ImportError:
            import hashlib
            m = hashlib.md5(open(self.ADDON_XML, "r", encoding="UTF-8").read().encode("UTF-8")).hexdigest()
 
        # save file
        try:
            self._save_file(m.encode("UTF-8"), file=self.ADDON_XML_MD5)
        except Exception as e:
            # oops
            print("An error occurred creating addons.xml.md5 file!\n%s" % e)
 
    def _save_file(self, data, file):
        try:
            # write data to the file (use b for Python 3)
            open(file, "wb").write(data)
        except Exception as e:
            # oops
            print("An error occurred saving %s file!\n%s" % (file, e))
            
    def _make_zipfile(self, output_filename, root_dir, base_dir):
        with zipfile.ZipFile(output_filename + ".zip", "w", zipfile.ZIP_DEFLATED) as zip:
            for root, dirs, files in os.walk(root_dir):
                relroot = os.path.relpath(root, root_dir)
                
                # skip .git folders
                if (relroot.startswith(".git")):
                    continue

                # skip media sub folders and themes folder
                if (relroot.startswith("media/") or relroot.startswith("themes")):
                	continue

                # adds base dir
                zip.write(root, os.path.join(base_dir, relroot))
                
                # add files
                for file in files:
                    # skip .git files
                    if (file.startswith(".git")):
                        continue

                    # skip media files
                    if (relroot.startswith("media") and not file.endswith(self.TEXTURE_EXTENSION)):
                		continue
                        
                    filename = os.path.join(root, file)
                    if os.path.isfile(filename): # regular files only
                        arcname = os.path.join(base_dir, relroot, file)
                        zip.write(filename, arcname)
 
if (__name__ == "__main__"):
    # start
    Generator()