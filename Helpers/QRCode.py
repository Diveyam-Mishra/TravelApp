import qrcode
import json
def generate_qr_code(data: dict, output_path: str):
    # Convert dictionary to JSON string
    json_data = json.dumps(data)
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(json_data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    img.save(output_path)