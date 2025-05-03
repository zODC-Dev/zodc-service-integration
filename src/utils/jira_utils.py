from typing import Any, Dict, Optional, Union


def convert_html_to_adf(html: str) -> Dict[str, Any]:
    """Convert HTML to ADF"""
    from bs4 import BeautifulSoup

    # Initialize empty ADF document structure
    adf = {
        "version": 1,
        "type": "doc",
        "content": []
    }

    if not html:
        return adf

    # Parse HTML
    soup = BeautifulSoup(html, 'html.parser')

    # Helper function to process text nodes
    def create_text_node(text):
        return {
            "type": "text",
            "text": text
        }

    # Helper function to process paragraphs
    def process_paragraph(element):
        para = {
            "type": "paragraph",
            "content": []
        }

        for child in element.children:
            if child.name == 'strong' or child.name == 'b':
                para["content"].append({
                    "type": "text",
                    "text": child.get_text(),
                    "marks": [{"type": "strong"}]
                })
            elif child.name == 'em' or child.name == 'i':
                para["content"].append({
                    "type": "text",
                    "text": child.get_text(),
                    "marks": [{"type": "em"}]
                })
            elif child.name == 'a':
                para["content"].append({
                    "type": "text",
                    "text": child.get_text(),
                    "marks": [{
                        "type": "link",
                        "attrs": {"href": child.get('href', '')}
                    }]
                })
            elif isinstance(child, str):
                text = child.strip()
                if text:
                    para["content"].append(create_text_node(text))

        return para

    # Process HTML elements
    for element in soup.children:
        if isinstance(element, str):
            if element.strip():
                adf["content"].append({
                    "type": "paragraph",
                    "content": [create_text_node(element.strip())]
                })
        elif element.name == 'p':
            adf["content"].append(process_paragraph(element))
        elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(element.name[1])
            adf["content"].append({
                "type": "heading",
                "attrs": {"level": level},
                "content": [create_text_node(element.get_text().strip())]
            })
        elif element.name == 'ul':
            list_items = []
            for li in element.find_all('li', recursive=False):
                list_items.append({
                    "type": "listItem",
                    "content": [process_paragraph(li)]
                })
            if list_items:
                adf["content"].append({
                    "type": "bulletList",
                    "content": list_items
                })
        elif element.name == 'ol':
            list_items = []
            for li in element.find_all('li', recursive=False):
                list_items.append({
                    "type": "listItem",
                    "content": [process_paragraph(li)]
                })
            if list_items:
                adf["content"].append({
                    "type": "orderedList",
                    "content": list_items
                })

    return adf


def convert_adf_to_text(adf_data: Union[str, Dict[str, Any], None]) -> Optional[str]:
    """Convert Atlassian Document Format to plain text"""
    if adf_data is None:
        return None

    if isinstance(adf_data, str):
        return adf_data

    try:
        # Xử lý ADF object
        if isinstance(adf_data, dict):
            text_parts = []

            # Lấy text từ content
            if "content" in adf_data:
                for content in adf_data["content"]:
                    if content.get("type") == "paragraph":
                        for text_node in content.get("content", []):
                            if text_node.get("type") == "text":
                                text_parts.append(text_node.get("text", ""))

            return "\n".join(text_parts) if text_parts else None

        return str(adf_data)

    except Exception:
        return None
