import os
import json
import PyPDF2
from lxml import etree
import xml.dom.minidom
import re
import base64

PDF_FILENAME = "ASA12610-25.pdf"  # <-- Change as required
OUTPUT_DIR = "xfa_extracted"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "xfa_bundle.json")
IGNORE_FILES = set(['.DS_Store'])

def remove_processing_instructions(xml_text):
    """Removes all XML processing instructions (<?...?>)."""
    return re.sub(r"<\?.*?\?>", "", xml_text, flags=re.DOTALL)

def xfa_to_pretty_xmls(pdf_file, out_folder):
    os.makedirs(out_folder, exist_ok=True)
    with open(pdf_file, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        xfa = reader.xfa
        if not xfa:
            print("No XFA found in the PDF.")
            exit(1)
        if isinstance(xfa, dict):
            items = xfa.items()
        elif isinstance(xfa, (list, tuple)):
            items = ((xfa[i], xfa[i+1]) for i in range(0, len(xfa), 2))
        else:
            print("XFA format not recognized:", type(xfa))
            exit(1)
        for name, xml_data in items:
            try:
                dom = xml.dom.minidom.parseString(
                    xml_data if isinstance(xml_data, str) else xml_data.decode('utf-8', errors='replace'))
                pretty_xml = dom.toprettyxml()
                outfn = f"{name}.xml"
                outpath = os.path.join(out_folder, outfn)
                with open(outpath, "w", encoding="utf-8") as xmlfile:
                    xmlfile.write(pretty_xml)
                print(f"Exported {outfn}")
            except Exception as e:
                print(f"Error parsing/writing XML for {name}: {e}")

def extract_and_replace_images(elem, image_folder, image_counter, parent_key=None):
    """
    Recursively scan an XML element for base64 images and extract them.
    Returns a dict representing the element, replacing base64 image data with a file path.
    """
    # Get local tag name without namespace
    tag = etree.QName(elem).localname
    result = {}
    # Copy attributes
    for k, v in elem.attrib.items():
        result['@'+k] = v

    # Check for common base64 image containers in XFA (image, exData, etc.)
    if tag == "image":
        img_b64 = (elem.text or '').strip()
        if img_b64:
            img_type = elem.attrib.get('contentType', 'image/png').split('/')[-1]  # fallback to png if uncertain
            image_counter[0] += 1
            img_name = f"image_{image_counter[0]}.{img_type}"
            os.makedirs(image_folder, exist_ok=True)
            img_path = os.path.join(image_folder, img_name)
            with open(img_path, "wb") as f:
                f.write(base64.b64decode(img_b64))
            result["image_path"] = os.path.relpath(img_path, OUTPUT_DIR)
        return result
    # exData with image contentType
    elif tag == "exData" and "image" in (elem.attrib.get("contentType") or ""):
        img_b64 = (elem.text or '').strip()
        img_type = elem.attrib["contentType"].split("/")[-1].split(";")[0]
        image_counter[0] += 1
        img_name = f"image_{image_counter[0]}.{img_type}"
        os.makedirs(image_folder, exist_ok=True)
        img_path = os.path.join(image_folder, img_name)
        with open(img_path, "wb") as f:
            f.write(base64.b64decode(img_b64))
        result["image_path"] = os.path.relpath(img_path, OUTPUT_DIR)
        return result
    # Otherwise, recursively scan child elements
    children = list(elem)
    if children:
        child_dict = {}
        for child in children:
            ctag = etree.QName(child).localname
            cdict = extract_and_replace_images(child, image_folder, image_counter, parent_key=tag)
            # Aggregate, merge lists if duplicate keys
            if ctag in child_dict:
                if not isinstance(child_dict[ctag], list):
                    child_dict[ctag] = [child_dict[ctag]]
                child_dict[ctag].append(cdict)
            else:
                child_dict[ctag] = cdict
        result.update(child_dict)
    # Add text if present
    text = (elem.text or '').strip()
    if text and not result:
        return text
    elif text:
        result['#text'] = text

    return result

def xmls_to_json_extract_images(out_folder, out_json, images_dir):
    bundle = {}
    xml_files = [f for f in os.listdir(out_folder) if f.endswith('.xml') and f not in IGNORE_FILES]
    image_counter = [0]
    for xmlfile in xml_files:
        abs_path = os.path.join(out_folder, xmlfile)
        key = os.path.splitext(xmlfile)[0]
        print(f"Parsing {xmlfile} ...")
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                xml_text = f.read()
            # Remove PI
            xml_text_clean = remove_processing_instructions(xml_text)
            root = etree.fromstring(xml_text_clean.encode("utf-8"))
            xml_dict = extract_and_replace_images(root, images_dir, image_counter)
            bundle[key] = xml_dict
        except Exception as e:
            print(f"Warning: Couldn't parse {xmlfile} ({e})")
    if image_counter[0]:
        bundle['image_folder'] = os.path.relpath(images_dir, out_folder)
    with open(out_json, "w", encoding="utf-8") as jf:
        json.dump(bundle, jf, indent=2, ensure_ascii=False)
    print(f"\n✔️  Bundle with image links written: {out_json}")

if __name__ == "__main__":
    print(f"Step 1: Extracting XFA XML packets from {PDF_FILENAME} ...")
    xfa_to_pretty_xmls(PDF_FILENAME, OUTPUT_DIR)
    print("\nStep 2: Parsing XMLs, extracting images, and bundling to JSON ...")
    xmls_to_json_extract_images(OUTPUT_DIR, OUTPUT_JSON, IMAGES_DIR)
    print("\nAll done.\nOpen your JSON for further processing and images in /images folder!")