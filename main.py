import binascii, hashlib, hmac
import os, requests
import threading
import xmltodict
s = requests.Session()
s.headers["user-agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"

from nps import NPS, nps_psm_entry
nps = NPS()

key = binascii.unhexlify("5AE4E16B214290E14366E5B653C4E3C3E69E4956510EADD66ACB37A077E0686E086F8BAB5030E3D82407F01B676CB8037DF20D1420C08A91A2141A3FE5DC063C")

def title_hash(title: str) -> str: # ex: NPPA00236_00
    h = hmac.new(key, title.encode("utf8"), hashlib.sha1)
    return h.hexdigest()[:8].upper()

def titleid_base_url(titleid: str, ver: str):
    titleid_full = titleid + "_00"
    return f"http://zeus.dl.playstation.net/psm/np/{titleid[0:4]}/{titleid_full}_{title_hash(titleid_full)}/{ver}"

def get_title_metadata(titleid: str, ver: str) -> str:
    " gets title metadata xml "
    r = s.get(f"{titleid_base_url(titleid, ver)}/metadata.xml")
    if r.status_code != 200:
        print(titleid, "metadata", r.status_code)
        return None
    return r.text

def get_title_version(titleid: str) -> str:
    " gets title metadata xml "
    r = s.get(titleid_base_url(titleid, "version.xml"))
    if r.status_code != 200:
        print(titleid, "metadata", r.status_code)
        return None
    return r.text

def get_versions_before(current: str) -> list[str]:
    major, minor = current.split(".")
    major = int(major)
    minor = int(minor)
    ret = []
    for i_major in range(1, major+1):
        for i_minor in range(0, minor+1):
            ret.append(f"{i_major}.{i_minor:02d}")
    return ret


def archive_entry(entry: nps_psm_entry, sem: threading.BoundedSemaphore):
    dir_path = os.path.join("archived", entry.content_id)
    print(entry.title_id)

    # get current version
    version_path = os.path.join(dir_path, "version.xml")
    if not os.path.exists(version_path):
        if version_xml := get_title_version(entry.title_id):
            os.makedirs(dir_path, exist_ok=True)
            with open(version_path, "w", encoding="utf8") as f:
                f.write(version_xml)
        else:
            print("No version")
            with open("missing.txt", "a", encoding="utf8") as f:
                    f.write(f"{entry.title_id}  {entry.name}\n")
    
    # read current version
    if os.path.exists(version_path):
        with open(version_path, "r", encoding="utf8") as f:
            version_data = xmltodict.parse(f.read())
        current_version = version_data["version"]["appVersion"]
    else:
        print("Version not found, using 1.00")
        current_version = "1.00"

    # archive each version before and including this
    versions = get_versions_before(current_version)
    for version in versions:
        print(f"{version}/{current_version}")
        versioned_dir = os.path.join(dir_path, version)

        # get metadata
        metadata_path = os.path.join(versioned_dir, "metadata.xml")
        if not os.path.exists(metadata_path):
            if metadata := get_title_metadata(entry.title_id, version):
                os.makedirs(versioned_dir, exist_ok=True)
                with open(metadata_path, "w", encoding="utf8") as f:
                    f.write(metadata)
            else:
                print("No metadata")
                continue

        # parse metadata
        with open(metadata_path, "r", encoding="utf8") as f:
            metadata = xmltodict.parse(f.read())

        for ss in metadata["psmMeta"]["screenShotList"]["screenShot"]:
            ss_path = os.path.join(versioned_dir, ss)
            if os.path.exists(ss_path):
                print("Skip", ss_path)
                continue

            print(ss)
            r = s.get(f"{titleid_base_url(entry.title_id, version)}/{ss}")
            with open(ss_path, "wb") as f:
                f.write(r.content)
    print()
    sem.release()


def main():
    # sanity check
    assert get_title_metadata("NPNA00133", "1.00")

    with open("missing.txt", "wb"):
        pass

    sem = threading.BoundedSemaphore(30)
    for entry in nps.entries[1:]:
        sem.acquire()
        threading.Thread(target=archive_entry, args=[entry, sem]).start()

if __name__ == "__main__":
    main()