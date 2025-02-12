import pandas as pd
import qrcode
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from io import BytesIO

source_df = pd.DataFrame({
    'item_code': ['ITEM001', 'ITEM002', 'ITEM003'],
    'item_name': ['Item Name 1', 'Item Name 2', 'Item Name 3']
})

#- Set Page Size -#
PAGE_WIDTH = 1.96 * inch
PAGE_HEIGHT = 0.78 * inch
qr_width = PAGE_WIDTH * 0.4
qr_height = PAGE_HEIGHT

#- Define Result File Name -#
result_file_name = 'generated_qr_codes.pdf'
canvas_object = canvas.Canvas(result_file_name, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

def get_optimal_font_size(text, max_width, max_height, initial_size=10):
    '''
    Calculate the optimal font size for the given text based on the maximum allowed width and height.

    Parameters:
    text (str): The text to be measured.
    max_width (float): The maximum allowed width for the text.
    max_height (float): The maximum allowed height for the text.
    initial_size (float): The initial font size to be used (default: 10).

    Returns:
    tuple: Returns the optimal font size and the corresponding ParagraphStyle object.
    '''
    font_size = initial_size
    while font_size > 1:
        style = ParagraphStyle(
            'CustomStyle',
            fontSize=font_size,
            leading=font_size * 1.0,
            alignment=1,
            wordWrap='CJK',
            fontName='Times-Roman'
        )
        p = Paragraph(text, style)
        w, h = p.wrap(max_width, max_height)
        if w <= max_width and h <= max_height:
            return font_size, style
        font_size -= 0.5
    return font_size, ParagraphStyle(
        'CustomStyle',
        fontSize=font_size,
        leading=font_size * 1.0,
        alignment=1,
        wordWrap='CJK',
        fontName='Times-Roman'
    )

#- Generate QR Code -#
for _, row in source_df.iterrows():
    qr_data = row['item_code']
    text_label = row['item_name']

    if len(text_label) > 50:
        text_label = text_label[:47] + "..."
    
    if len(qr_data) > 50:
        qr_data = qr_data[:47] + "..."

    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill='black', back_color='white')

    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)

    x_qr = 0
    y_qr = 0

    text_width = PAGE_WIDTH - qr_width - 10
    text_height = PAGE_HEIGHT / 2 - 5
    x_text = qr_width + 5
    
    font_size_transno, style_transno = get_optimal_font_size(
        qr_data, 
        text_width, 
        text_height,
        initial_size=9.5
    )
    style_transno.fontName = 'Times-Bold'
    
    font_size_name, style_name = get_optimal_font_size(
        text_label, 
        text_width, 
        text_height,
        initial_size=9
    )
    style_name.fontName = 'Times-Roman'
    
    p_transno = Paragraph(qr_data, style_transno)
    p_name = Paragraph(text_label, style_name)
    
    w_transno, h_transno = p_transno.wrap(text_width, text_height)
    w_name, h_name = p_name.wrap(text_width, text_height)
    
    canvas_object.drawImage(ImageReader(buffer), x_qr, y_qr, width=qr_width, height=qr_height)

    total_text_height = h_transno + h_name + 5
    start_y = (PAGE_HEIGHT - total_text_height) / 2
    
    y_transno = start_y + h_name + 5
    y_name = start_y

    p_transno.drawOn(canvas_object, x_text, y_transno)
    p_name.drawOn(canvas_object, x_text, y_name)

    canvas_object.showPage()
canvas_object.save()
print(f'PDF has been successfully saved as : {result_file_name}')
