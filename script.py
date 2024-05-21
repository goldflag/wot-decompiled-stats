import os
import json
from lxml import etree
from typing import Dict, List, Union

def xml_to_json(xml_file: str) -> Dict:
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(xml_file, parser=parser)
    root = tree.getroot()
    return xml_to_dict(root)

def is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False

def xml_to_dict(root: etree._Element) -> Dict:
    result: Dict[str, Union[str, int, float, List, Dict]] = {}
    for child in root:
        if child.tag == 'tags':
            if child.text is not None:
                result[child.tag] = [tag.strip() for tag in child.text.split()]
            else:
                result[child.tag] = []
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
            result[child.tag] = xml_to_dict(child)
    return result

def process_xml_files(source_dir: str, output_dir: str) -> None:
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.xml'):
                print(file)
                xml_path = os.path.join(root, file)
                json_data = xml_to_json(xml_path)
                
                relative_path = os.path.relpath(xml_path, source_dir)
                output_path = os.path.join(output_dir, relative_path[:-4] + '.json')
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'w') as json_file:
                    json.dump(json_data, json_file, indent=4)

def main() -> None:
    source_dir = 'WorldOfTanks-Decompiled/source/res/scripts/item_defs/vehicles'
    output_dir = 'output'
    
    process_xml_files(source_dir, output_dir)

if __name__ == '__main__':
    main()