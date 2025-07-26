import PyPDF2
import xml.dom.minidom

PDF_FILENAME = "xfa-example.pdf"

with open(PDF_FILENAME, "rb") as f:
    reader = PyPDF2.PdfReader(f)
    xfa = reader.xfa

    if not xfa:
        print("No XFA found in the PDF.")
    else:
        if isinstance(xfa, dict):
            for name, xml_data in xfa.items():
                # Pretty-print the XML
                try:
                    dom = xml.dom.minidom.parseString(xml_data)
                    pretty_xml = dom.toprettyxml()
                    filename = f"{name}.xml"
                    # Save to file
                    with open(filename, "w", encoding="utf-8") as xmlfile:
                        xmlfile.write(pretty_xml)
                    print(f"Exported {filename}")
                except Exception as e:
                    print("Error parsing/writing XML for", name, ":", e)
        elif isinstance(xfa, (list, tuple)):
            for i in range(0, len(xfa), 2):
                name = xfa[i]
                xml_data = xfa[i + 1]
                try:
                    dom = xml.dom.minidom.parseString(xml_data)
                    pretty_xml = dom.toprettyxml()
                    filename = f"{name}.xml"
                    with open(filename, "w", encoding="utf-8") as xmlfile:
                        xmlfile.write(pretty_xml)
                    print(f"Exported {filename}")
                except Exception as e:
                    print("Error parsing/writing XML for", name, ":", e)
        else:
            print("XFA format not recognized:", type(xfa))