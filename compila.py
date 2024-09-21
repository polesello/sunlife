from PyPDF2 import PdfWriter, PdfReader
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm


path = 'media/documents/iva.pdf'

packet = io.BytesIO()
can = canvas.Canvas(packet, pagesize=letter)
can.drawString(4.7*cm, 24.8*cm, "Nello Polesello")
can.drawString(3.4*cm, 23.9*cm, "Via San antonio 1")
can.drawString(2.4*cm, 23.1*cm, "PLSNLL73M18G888I")
can.drawString(5.5*cm, 18.2*cm, "San Giorio di Susa, TO 10050")
can.drawString(3.5*cm, 9.5*cm, "Torino, 7 ottobre 2023")

can.save()

#move to the beginning of the StringIO buffer
packet.seek(0)

# create a new PDF with Reportlab
new_pdf = PdfReader(packet)
# read your existing PDF
existing_pdf = PdfReader(open(path, "rb"))
output = PdfWriter()
# add the "watermark" (which is the new pdf) on the existing page
page = existing_pdf.pages[0]
page.merge_page(new_pdf.pages[0])
output.add_page(page)
# finally, write "output" to a real file
output_stream = open("media/documents/compilato.pdf", "wb")
output.write(output_stream)
output_stream.close()