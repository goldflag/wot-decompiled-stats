import os
from lxml import etree
from typing import Any, Dict, List, Union
import json
import re
import polib

nation_conv = {
    "usa": "USA",
    "china": "China",
    "czech": "Czech",
    "france": "France",
    "germany": "Germany",
    "italy": "Italy",
    "japan": "Japan",
    "poland": "Poland",
    "sweden": "Sweden",
    "uk": "UK",
    "ussr": "USSR",
}

class_conv = {
    "lightTank": "LT",
    "mediumTank": "MT",
    "heavyTank": "HT",
    "AT-SPG": "TD",
    "SPG": "SPG",
}

def is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False

def get_msgstr(nation: str, msgid: str) -> str | None:

    # If the nation is 'uk', change it to 'gb' to match the .po file name
    if nation == 'uk':
        nation = 'gb'

    path = os.path.join('wot-src', 'sources', 'res', 'text', 'lc_messages', f'{nation}_vehicles.po')
    try:
        # Load the .po file
        po = polib.pofile(path)
        
        # Find the entry with the given msgid
        entry = po.find(msgid)
        
        # If the entry is found, return the msgstr, otherwise return None
        if entry:
            return entry.msgstr
        else:
            return None
    except FileNotFoundError:
        print(f'Error: The file {path} was not found.')
        return None
    except IOError as e:
        print(f'Error: There was a problem reading the file: {e}')
        return None
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        return None

def xml_to_json(xml_file: str) -> Dict:
    # Read the XML content from the file
    with open(xml_file, 'r', encoding='utf-8') as file:
        xml_content = file.read()
    
    # Remove XML comments using a regular expression
    cleaned_xml_content = re.sub(r'<!--.*?-->', '', xml_content, flags=re.DOTALL)
    
    # Convert cleaned XML content to bytes
    cleaned_xml_content_bytes = cleaned_xml_content.encode('utf-8')
    
    # Parse the cleaned XML content as bytes
    parser = etree.XMLParser(recover=True)
    tree = etree.fromstring(cleaned_xml_content_bytes, parser=parser)
    
    # Convert the XML tree to a dictionary
    xml_dict = xml_to_dict(tree, os.path.basename(xml_file))
    return xml_dict

def xml_to_dict(root: etree._Element, file: str) -> Dict:
    result: Dict[str, Union[str, int, float, List, Dict]] = {}
    for child in root:
        if child.tag == 'tags':
            if child.text is not None:
                result[child.tag] = [tag.strip() for tag in child.text.split()]
            else:
                result[child.tag] = []
        elif child.tag == 'price' and file == 'list.xml' and child.find('gold') is not None:
            result[child.tag] = { 'gold': int(child.text.strip()) }
        elif len(child) == 0:
            if child.text is not None:
                text = child.text.strip()
                if text.isdigit():
                    result[child.tag] = int(text)
                elif is_float(text):
                    result[child.tag] = float(text)
                elif ' ' in text:
                    values = text.split()
                    if all(is_float(val) for val in values):
                        result[child.tag] = [float(val) for val in values]
                    else:
                        result[child.tag] = values
                else:
                    result[child.tag] = text
            else:
                result[child.tag] = None
        else:
            result[child.tag] = xml_to_dict(child, file)
    return result