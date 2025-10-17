import io
import qrcode
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import database as db

# ลงทะเบียน Thai fonts (ถ้ามี)
try:
    pdfmetrics.registerFont(TTFont('THSarabunNew', '/usr/share/fonts/truetype/thai/THSarabunNew.ttf'))
    pdfmetrics.registerFont(TTFont('THSarabunNew-Bold', '/usr/share/fonts/truetype/thai/THSarabunNew Bold.ttf'))
    THAI_FONT = 'THSarabunNew'
    THAI_FONT_BOLD = 'THSarabunNew-Bold'
except:
    # ถ้าไม่มี font ไทย ใช้ default
    THAI_FONT = 'Helvetica'
    THAI_FONT_BOLD = 'Helvetica-Bold'


def generate_qr_code(reference_id, size=100):
    """สร้าง QR Code สำหรับ reference ID"""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    verification_url = f"https://floorprice.example.com/verify/{reference_id}"
    qr.add_data(verification_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to BytesIO
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img_buffer


def format_currency(amount):
    """จัดรูปแบบตัวเลขเป็นสกุลเงิน"""
    return f"{amount:,.2f}"


def generate_verification_document_html(log):
    """
    สร้างเอกสารแบบ HTML สำหรับพิมพ์/บันทึก
    """
    customer_type_th = "🏠 Residential (บ้าน)" if log.customer_type == 'residential' else "🏢 Business (ธุรกิจ)"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>เอกสารยืนยันการตรวจสอบราคา - {log.reference_id}</title>
        <style>
            @media print {{
                @page {{ margin: 20mm; }}
                body {{ margin: 0; }}
            }}
            body {{
                font-family: 'Sarabun', 'Arial', sans-serif;
                max-width: 210mm;
                margin: 0 auto;
                padding: 20px;
                background: white;
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #0066cc;
                padding-bottom: 15px;
                margin-bottom: 25px;
            }}
            .header h1 {{
                color: #0066cc;
                margin: 0;
                font-size: 24pt;
            }}
            .header .subtitle {{
                color: #666;
                font-size: 12pt;
                margin-top: 5px;
            }}
            .reference-box {{
                background: #f0f8ff;
                border: 2px solid #0066cc;
                border-radius: 8px;
                padding: 15px;
                margin: 20px 0;
                text-align: center;
            }}
            .reference-box .ref-label {{
                font-size: 10pt;
                color: #666;
                margin-bottom: 5px;
            }}
            .reference-box .ref-id {{
                font-size: 14pt;
                font-weight: bold;
                color: #0066cc;
                font-family: 'Courier New', monospace;
            }}
            .section {{
                margin: 20px 0;
                page-break-inside: avoid;
            }}
            .section-title {{
                background: #0066cc;
                color: white;
                padding: 8px 15px;
                font-size: 14pt;
                font-weight: bold;
                margin-bottom: 10px;
                border-radius: 4px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }}
            table th {{
                background: #e6f2ff;
                color: #0066cc;
                padding: 10px;
                text-align: left;
                font-weight: bold;
                border: 1px solid #0066cc;
            }}
            table td {{
                padding: 8px 10px;
                border: 1px solid #ddd;
            }}
            table tr:nth-child(even) {{
                background: #f9f9f9;
            }}
            .result-box {{
                border: 3px solid;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                text-align: center;
            }}
            .result-box.pass {{
                background: #d4edda;
                border-color: #28a745;
                color: #155724;
            }}
            .result-box.fail {{
                background: #f8d7da;
                border-color: #dc3545;
                color: #721c24;
            }}
            .result-box .result-title {{
                font-size: 18pt;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .result-box .result-detail {{
                font-size: 14pt;
            }}
            .comparison-table {{
                margin: 15px 0;
            }}
            .comparison-table td {{
                padding: 10px;
            }}
            .comparison-table .label {{
                font-weight: bold;
                width: 40%;
                background: #f0f0f0;
            }}
            .comparison-table .value {{
                text-align: right;
                font-family: 'Courier New', monospace;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 2px solid #ddd;
                text-align: center;
                font-size: 9pt;
                color: #666;
            }}
            .signature-box {{
                margin-top: 40px;
                display: flex;
                justify-content: space-around;
            }}
            .signature {{
                text-align: center;
                width: 40%;
            }}
            .signature-line {{
                border-top: 1px solid #000;
                margin-top: 60px;
                padding-top: 5px;
            }}
            .watermark {{
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) rotate(-45deg);
                font-size: 72pt;
                color: rgba(0, 102, 204, 0.1);
                font-weight: bold;
                z-index: -1;
                pointer-events: none;
            }}
            @media print {{
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="watermark">VERIFIED</div>
        
        <div class="header">
            <h1>📋 เอกสารยืนยันการตรวจสอบราคา</h1>
            <div class="subtitle">Floor Price Verification Document</div>
        </div>
        
        <div class="reference-box">
            <div class="ref-label">รหัสอ้างอิง / Reference ID</div>
            <div class="ref-id">{log.reference_id}</div>
            <div style="margin-top: 10px; font-size: 9pt; color: #666;">
                ตรวจสอบความถูกต้องได้ที่: https://floorprice.example.com/verify/{log.reference_id}
            </div>
        </div>
        
        <!-- ข้อมูลการตรวจสอบ -->
        <div class="section">
            <div class="section-title">📝 ข้อมูลการตรวจสอบ</div>
            <table class="comparison-table">
                <tr>
                    <td class="label">ผู้ตรวจสอบ</td>
                    <td class="value">{log.user_email}</td>
                </tr>
                <tr>
                    <td class="label">วันที่ตรวจสอบ</td>
                    <td class="value">{log.checked_at.strftime('%d/%m/%Y %H:%M:%S')}</td>
                </tr>
                <tr>
                    <td class="label">ประเภทลูกค้า</td>
                    <td class="value">{customer_type_th}</td>
                </tr>
            </table>
        </div>
        
        <!-- รายละเอียดแพ็คเกจ -->
        <div class="section">
            <div class="section-title">📦 รายละเอียดแพ็คเกจ</div>
            <table class="comparison-table">
                <tr>
                    <td class="label">ความเร็วอินเทอร์เน็ต</td>
                    <td class="value">{log.speed} Mbps</td>
                </tr>
                <tr>
                    <td class="label">ระยะทางติดตั้ง</td>
                    <td class="value">{log.distance} กม.</td>
                </tr>
                <tr>
                    <td class="label">อุปกรณ์</td>
                    <td class="value">{log.equipment}</td>
                </tr>
                <tr>
                    <td class="label">ระยะสัญญา</td>
                    <td class="value">{log.contract_months} เดือน</td>
                </tr>
                <tr>
                    <td class="label">Fixed IP</td>
                    <td class="value">{'✅ มี' if log.has_fixed_ip else '❌ ไม่มี'}</td>
                </tr>
            </table>
        </div>
        
        <!-- การคำนวณราคา -->
        <div class="section">
            <div class="section-title">💰 การคำนวณราคา</div>
            <table class="comparison-table">
                <tr>
                    <td class="label">ราคาที่เสนอขาย</td>
                    <td class="value">{format_currency(log.proposed_price)} บาท/เดือน</td>
                </tr>
                <tr>
                    <td class="label">ส่วนลด ({log.discount_percent}%)</td>
                    <td class="value">-{format_currency(log.proposed_price * log.discount_percent / 100)} บาท</td>
                </tr>
                <tr style="background: #fffacd;">
                    <td class="label" style="font-weight: bold;">ราคาหลังหักส่วนลด</td>
                    <td class="value" style="font-weight: bold;">{format_currency(log.proposed_price * (1 - log.discount_percent/100))} บาท</td>
                </tr>
                <tr>
                    <td class="label">หัก: ค่าธรรมเนียม กสทช. (4%)</td>
                    <td class="value">-{format_currency(log.regulator_fee)} บาท</td>
                </tr>
                <tr style="background: #d4edda;">
                    <td class="label" style="font-weight: bold; font-size: 12pt;">รายได้สุทธิ</td>
                    <td class="value" style="font-weight: bold; font-size: 12pt; color: #28a745;">{format_currency(log.net_revenue)} บาท/เดือน</td>
                </tr>
            </table>
        </div>
        
        <!-- Floor Price -->
        <div class="section">
            <div class="section-title">📊 Floor Price (ราคาขั้นต่ำ)</div>
            <table class="comparison-table">
                <tr>
                    <td class="label">Floor - ลูกค้าเดิม (ไม่รวมค่าติดตั้ง)</td>
                    <td class="value">{format_currency(log.floor_existing)} บาท/เดือน</td>
                </tr>
                <tr>
                    <td class="label">Floor - ลูกค้าใหม่ (รวมค่าติดตั้ง amortized)</td>
                    <td class="value">{format_currency(log.floor_new)} บาท/เดือน</td>
                </tr>
                <tr style="background: #e6f2ff;">
                    <td class="label" style="font-weight: bold;">Floor - ถัวเฉลี่ย ({log.existing_customer_ratio*100:.0f}% เดิม / {log.new_customer_ratio*100:.0f}% ใหม่)</td>
                    <td class="value" style="font-weight: bold; color: #0066cc;">{format_currency(log.floor_weighted)} บาท/เดือน</td>
                </tr>
            </table>
        </div>
        
        <!-- ผลการตรวจสอบ -->
        <div class="section">
            <div class="section-title">✅ ผลการตรวจสอบ</div>
            
            <table style="margin-top: 15px;">
                <tr>
                    <th style="width: 30%;">เปรียบเทียบกับ</th>
                    <th style="width: 25%; text-align: right;">Margin (บาท)</th>
                    <th style="width: 20%; text-align: right;">Margin (%)</th>
                    <th style="width: 25%; text-align: center;">ผลการตรวจสอบ</th>
                </tr>
                <tr>
                    <td>ลูกค้าเดิม</td>
                    <td style="text-align: right; font-family: 'Courier New', monospace;">{format_currency(log.margin_existing_baht)}</td>
                    <td style="text-align: right; font-family: 'Courier New', monospace;">{log.margin_existing_percent:.2f}%</td>
                    <td style="text-align: center; font-weight: bold; color: {'#28a745' if log.is_valid_existing else '#dc3545'};">
                        {'✅ ผ่าน' if log.is_valid_existing else '❌ ไม่ผ่าน'}
                    </td>
                </tr>
                <tr>
                    <td>ลูกค้าใหม่</td>
                    <td style="text-align: right; font-family: 'Courier New', monospace;">{format_currency(log.margin_new_baht)}</td>
                    <td style="text-align: right; font-family: 'Courier New', monospace;">{log.margin_new_percent:.2f}%</td>
                    <td style="text-align: center; font-weight: bold; color: {'#28a745' if log.is_valid_new else '#dc3545'};">
                        {'✅ ผ่าน' if log.is_valid_new else '❌ ไม่ผ่าน'}
                    </td>
                </tr>
                <tr style="background: #f0f8ff;">
                    <td style="font-weight: bold;">ถัวเฉลี่ย</td>
                    <td style="text-align: right; font-family: 'Courier New', monospace; font-weight: bold;">{format_currency(log.margin_weighted_baht)}</td>
                    <td style="text-align: right; font-family: 'Courier New', monospace; font-weight: bold;">{log.margin_weighted_percent:.2f}%</td>
                    <td style="text-align: center; font-weight: bold; color: {'#28a745' if log.is_valid_weighted else '#dc3545'};">
                        {'✅ ผ่าน' if log.is_valid_weighted else '❌ ไม่ผ่าน'}
                    </td>
                </tr>
            </table>
        </div>
        
        <!-- ผลการตรวจสอบขั้นสุดท้าย -->
        <div class="result-box {'pass' if log.is_valid_weighted else 'fail'}">
            <div class="result-title">
                {'✅ ราคาผ่านการตรวจสอบ' if log.is_valid_weighted else '❌ ราคาไม่ผ่านการตรวจสอบ'}
            </div>
            <div class="result-detail">
                {'ราคาที่เสนอสูงกว่า Floor Price ถัวเฉลี่ย' if log.is_valid_weighted else 'ราคาที่เสนอต่ำกว่า Floor Price ถัวเฉลี่ย'}
            </div>
            <div class="result-detail" style="margin-top: 10px; font-size: 16pt;">
                Margin: {log.margin_weighted_percent:.2f}% 
                ({'+' if log.margin_weighted_baht >= 0 else ''}{format_currency(log.margin_weighted_baht)} บาท)
            </div>
        </div>
        
        {f'''
        <!-- หมายเหตุ -->
        <div class="section">
            <div class="section-title">📝 หมายเหตุ</div>
            <div style="padding: 10px; background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px;">
                {log.notes}
            </div>
        </div>
        ''' if log.notes else ''}
        
        <!-- ลายเซ็น -->
        <div class="signature-box no-print">
            <div class="signature">
                <div class="signature-line">ผู้ตรวจสอบ / Checked by</div>
                <div style="margin-top: 5px; font-size: 10pt;">{log.user_email}</div>
            </div>
            <div class="signature">
                <div class="signature-line">ผู้อนุมัติ / Approved by</div>
                <div style="margin-top: 5px; font-size: 10pt;">_______________________</div>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p><strong>คำเตือน:</strong> เอกสารฉบับนี้ได้รับการตรวจสอบและบันทึกในระบบ Floor Price Validator</p>
            <p>Reference ID: <code>{log.reference_id}</code> | 
            สร้างเมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p style="color: #999; font-size: 8pt;">
                เอกสารนี้สามารถตรวจสอบความถูกต้องได้ทางระบบ<br>
                หากพบการปลอมแปลงจะถือเป็นความผิดตามกฎหมาย
            </p>
        </div>
        
        <script>
            // Auto print when opened
            // window.onload = function() {{ window.print(); }}
        </script>
    </body>
    </html>
    """
    
    return html


def generate_simple_summary_text(log):
    """สร้างข้อความสรุปแบบง่าย (สำหรับ copy-paste)"""
    customer_type_th = "Residential" if log.customer_type == 'residential' else "Business"
    
    text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     เอกสารยืนยันการตรวจสอบราคา
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Reference ID: {log.reference_id}
วันที่ตรวจสอบ: {log.checked_at.strftime('%d/%m/%Y %H:%M')}
ผู้ตรวจสอบ: {log.user_email}

━━━ รายละเอียดแพ็คเกจ ━━━
• ประเภทลูกค้า: {customer_type_th}
• ความเร็ว: {log.speed} Mbps
• ระยะทาง: {log.distance} กม.
• สัญญา: {log.contract_months} เดือน
• Fixed IP: {'✓ มี' if log.has_fixed_ip else '✗ ไม่มี'}

━━━ การคำนวณราคา ━━━
ราคาที่เสนอ: {format_currency(log.proposed_price)} บาท
ส่วนลด ({log.discount_percent}%): -{format_currency(log.proposed_price * log.discount_percent / 100)} บาท
ค่าธรรมเนียม (4%): -{format_currency(log.regulator_fee)} บาท
รายได้สุทธิ: {format_currency(log.net_revenue)} บาท

━━━ Floor Price ━━━
• ลูกค้าเดิม: {format_currency(log.floor_existing)} บาท
• ลูกค้าใหม่: {format_currency(log.floor_new)} บาท
• ถัวเฉลี่ย: {format_currency(log.floor_weighted)} บาท

━━━ ผลการตรวจสอบ ━━━
{'✅ ผ่าน' if log.is_valid_weighted else '❌ ไม่ผ่าน'} - Margin: {log.margin_weighted_percent:.2f}% ({'+' if log.margin_weighted_baht >= 0 else ''}{format_currency(log.margin_weighted_baht)} บาท)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ตรวจสอบได้ที่: 
https://floorprice.example.com/verify/{log.reference_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    return text.strip()