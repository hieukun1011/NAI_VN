import re


def clean_address(address):
    # Danh sách các từ khóa cần loại bỏ
    remove_keywords = ['phường', 'quận', 'huyện', 'q.', 'p.', 'thành phố', 'tp', 'tp.', 'q', 'h', 'p', 'h.', 'xã',
                       'viet nam', 'Việt Nam']

    # Chuyển đổi địa chỉ và từ khóa thành chữ thường
    address_lower = address.lower()
    for i in range(len(remove_keywords)):
        remove_keywords[i] = remove_keywords[i].lower()

    # Loại bỏ các từ khóa
    for keyword in remove_keywords:
        address_lower = re.sub(r'\b{}\b'.format(re.escape(keyword)), '', address_lower)

    address_parts = [part.strip() for part in address_lower.split(',') if part.strip() != '']

    return address_parts
