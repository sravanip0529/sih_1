from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "PS26227_PROJECT_PPT.pptx"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Theme colors
NAVY = RGBColor(10, 23, 35)
BLUE = RGBColor(59, 130, 246)
CYAN = RGBColor(126, 211, 255)
WHITE = RGBColor(255, 255, 255)
LIGHT = RGBColor(224, 234, 240)
SLATE = RGBColor(71, 94, 110)
GREEN = RGBColor(74, 196, 130)
GOLD = RGBColor(245, 176, 80)
RED = RGBColor(201, 77, 77)


def add_title(slide, title, subtitle=None):
    title_box = slide.shapes.add_textbox(Inches(0.7), Inches(0.45), Inches(11.8), Inches(0.8))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.runs[0].font.size = Pt(26)
    p.runs[0].font.bold = True
    p.runs[0].font.color.rgb = WHITE
    if subtitle:
        sub = slide.shapes.add_textbox(Inches(0.7), Inches(1.0), Inches(11.5), Inches(0.4))
        stf = sub.text_frame
        sp = stf.paragraphs[0]
        sp.text = subtitle
        sp.runs[0].font.size = Pt(12)
        sp.runs[0].font.color.rgb = LIGHT


def apply_bg(slide, color=NAVY):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_footer(slide, text='PS26227 — Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery'):
    foot = slide.shapes.add_textbox(Inches(0.6), Inches(7.0), Inches(12.0), Inches(0.3))
    tf = foot.text_frame
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = PP_ALIGN.RIGHT
    p.runs[0].font.size = Pt(8)
    p.runs[0].font.color.rgb = LIGHT

# Slide 1
slide = prs.slides.add_slide(prs.slide_layouts[6])
apply_bg(slide)
add_title(slide, 'PS26227', 'Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery')
box = slide.shapes.add_textbox(Inches(0.9), Inches(1.8), Inches(11.5), Inches(2.8))
text = box.text_frame
p = text.paragraphs[0]
p.text = 'From Satellite Pixels to Searchable Change Intelligence'
p.runs[0].font.size = Pt(28)
p.runs[0].font.bold = True
p.runs[0].font.color.rgb = WHITE
p2 = text.add_paragraph()
p2.text = 'A project that turns multi-temporal satellite imagery into evidence-based, semantically searchable change regions.'
p2.runs[0].font.size = Pt(18)
p2.runs[0].font.color.rgb = LIGHT
add_footer(slide)

# Slide 2
slide = prs.slides.add_slide(prs.slide_layouts[6])
apply_bg(slide, NAVY)
add_title(slide, 'The Challenge', 'Manual interpretation of large multi-date imagery is slow and difficult.')

shape = slide.shapes.add_shape(1, Inches(0.9), Inches(1.7), Inches(11.3), Inches(4.2))
shape.fill.solid()
shape.fill.fore_color.rgb = RGBColor(17, 31, 43)
shape.line.color.rgb = CYAN

# left/right cards
for idx, (label, desc) in enumerate([
    ('June 2023', 'Reference observation'),
    ('June 2024', 'Current observation')
]):
    x = Inches(1.4 + idx * 5.0)
    card = slide.shapes.add_shape(1, x, Inches(2.2), Inches(4.1), Inches(2.2))
    card.fill.solid(); card.fill.fore_color.rgb = RGBColor(14, 24, 35)
    card.line.color.rgb = CYAN
    tf = card.text_frame
    p = tf.paragraphs[0]
    p.text = label
    p.runs[0].font.size = Pt(20); p.runs[0].font.bold = True; p.runs[0].font.color.rgb = WHITE
    p2 = tf.add_paragraph(); p2.text = desc; p2.runs[0].font.size = Pt(12); p2.runs[0].font.color.rgb = LIGHT

slide.shapes.add_textbox(Inches(1.1), Inches(5.8), Inches(10.7), Inches(0.8)).text_frame.paragraphs[0].text = 'How can we detect meaningful changes and search for them using natural language?'
add_footer(slide)

# Slide 3
slide = prs.slides.add_slide(prs.slide_layouts[6])
apply_bg(slide)
add_title(slide, 'System Overview', 'Satellite imagery to searchable change intelligence')

flow = [
    ('Sentinel-2 Images', 1.1),
    ('Quality-Aware Processing', 3.2),
    ('Change Detection', 5.3),
    ('Change Regions', 7.4),
    ('Semantic Retrieval', 9.5)
]
for label, x in flow:
    box = slide.shapes.add_shape(1, Inches(x), Inches(2.6), Inches(1.6), Inches(1.1))
    box.fill.solid(); box.fill.fore_color.rgb = RGBColor(24, 41, 54)
    box.line.color.rgb = CYAN
    tf = box.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = label; p.alignment = PP_ALIGN.CENTER
    p.runs[0].font.size = Pt(12); p.runs[0].font.bold = True; p.runs[0].font.color.rgb = WHITE
    if x < 9.5:
        arrow = slide.shapes.add_shape(1, Inches(x+1.55), Inches(3.1), Inches(0.3), Inches(0.15))
        arrow.fill.solid(); arrow.fill.fore_color.rgb = CYAN; arrow.line.color.rgb = CYAN

text = slide.shapes.add_textbox(Inches(1.2), Inches(5.0), Inches(10.8), Inches(1.2))
para = text.text_frame
p = para.paragraphs[0]
p.text = 'The system analyzes real Sentinel-2 imagery, filters unreliable pixels, detects spectral differences, groups evidence into regions, and enables natural-language retrieval over the results.'
p.runs[0].font.size = Pt(18); p.runs[0].font.color.rgb = LIGHT
add_footer(slide)

# Slide 4
slide = prs.slides.add_slide(prs.slide_layouts[6])
apply_bg(slide)
add_title(slide, 'Real Sentinel-2 Inputs', 'Reference and moving imagery from the same area')

img1 = slide.shapes.add_shape(1, Inches(0.9), Inches(1.8), Inches(4.8), Inches(3.4))
img1.fill.solid(); img1.fill.fore_color.rgb = RGBColor(27, 44, 61)
img1.line.color.rgb = CYAN
img1.text = 'Reference Image\n2023-06-05'
img1.text_frame.paragraphs[0].runs[0].font.size = Pt(18)
img1.text_frame.paragraphs[0].runs[0].font.bold = True

img2 = slide.shapes.add_shape(1, Inches(6.9), Inches(1.8), Inches(4.8), Inches(3.4))
img2.fill.solid(); img2.fill.fore_color.rgb = RGBColor(27, 44, 61)
img2.line.color.rgb = CYAN
img2.text = 'Moving Image\n2024-06-26'
img2.text_frame.paragraphs[0].runs[0].font.size = Pt(18)
img2.text_frame.paragraphs[0].runs[0].font.bold = True

meta = slide.shapes.add_textbox(Inches(2.2), Inches(5.7), Inches(8.8), Inches(0.7))
meta.text_frame.paragraphs[0].text = 'Sentinel-2 | Same Area of Interest | EPSG:32633 | 10 m resolution'
meta.text_frame.paragraphs[0].runs[0].font.size = Pt(16)
meta.text_frame.paragraphs[0].runs[0].font.color.rgb = LIGHT
add_footer(slide)

# Slide 5
slide = prs.slides.add_slide(prs.slide_layouts[6])
apply_bg(slide)
add_title(slide, 'Quality-Aware Processing', 'Reliable observations only')

mask = slide.shapes.add_shape(1, Inches(1.0), Inches(1.9), Inches(7.4), Inches(3.8))
mask.fill.solid(); mask.fill.fore_color.rgb = RGBColor(15, 27, 39)
mask.line.color.rgb = CYAN

legend = slide.shapes.add_shape(1, Inches(9.2), Inches(2.2), Inches(2.9), Inches(2.6))
legend.fill.solid(); legend.fill.fore_color.rgb = RGBColor(17, 28, 37)
legend.line.color.rgb = CYAN
lf = legend.text_frame
for idx, item in enumerate(['Valid pixels', 'Cloud pixels', 'No-data pixels']):
    p = lf.paragraphs[0] if idx == 0 else lf.add_paragraph()
    p.text = item
    p.runs[0].font.size = Pt(14)
    p.runs[0].font.color.rgb = WHITE

box = slide.shapes.add_textbox(Inches(1.2), Inches(5.8), Inches(9.7), Inches(0.8))
box.text_frame.paragraphs[0].text = 'Only jointly valid pixels are used for reliable comparison. Joint Valid Pixel Fraction: 97.48%'
box.text_frame.paragraphs[0].runs[0].font.size = Pt(18)
box.text_frame.paragraphs[0].runs[0].font.color.rgb = LIGHT
add_footer(slide)

# Slide 6
slide = prs.slides.add_slide(prs.slide_layouts[6])
apply_bg(slide)
add_title(slide, 'Change Detection', 'Spectral evidence across multiple bands')

left = slide.shapes.add_shape(1, Inches(0.9), Inches(1.8), Inches(3.8), Inches(2.7))
left.fill.solid(); left.fill.fore_color.rgb = RGBColor(20, 43, 56)
left.line.color.rgb = CYAN
left.text = 'Reference\nImage'
left.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
left.text_frame.paragraphs[0].runs[0].font.bold = True

mid = slide.shapes.add_shape(1, Inches(4.9), Inches(1.8), Inches(3.8), Inches(2.7))
mid.fill.solid(); mid.fill.fore_color.rgb = RGBColor(20, 43, 56)
mid.line.color.rgb = CYAN
mid.text = 'Moving\nImage'
mid.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
mid.text_frame.paragraphs[0].runs[0].font.bold = True

right = slide.shapes.add_shape(1, Inches(8.8), Inches(1.8), Inches(3.6), Inches(2.7))
right.fill.solid(); right.fill.fore_color.rgb = RGBColor(47, 32, 20)
right.line.color.rgb = GOLD
right.text = 'Change\nMagnitude'
right.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
right.text_frame.paragraphs[0].runs[0].font.bold = True

band_text = slide.shapes.add_textbox(Inches(1.5), Inches(5.5), Inches(9.8), Inches(0.5))
band_text.text_frame.paragraphs[0].text = 'Blue | Green | Red | Near Infrared | SWIR'
band_text.text_frame.paragraphs[0].runs[0].font.size = Pt(16)
band_text.text_frame.paragraphs[0].runs[0].font.color.rgb = LIGHT

warning = slide.shapes.add_textbox(Inches(0.9), Inches(6.1), Inches(11.5), Inches(0.5))
warning.text_frame.paragraphs[0].text = 'Detected change represents spectral change evidence, not automatically verified real-world change.'
warning.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
warning.text_frame.paragraphs[0].runs[0].font.color.rgb = GOLD
add_footer(slide)

# Slide 7
slide = prs.slides.add_slide(prs.slide_layouts[6])
apply_bg(slide)
add_title(slide, 'Change Regions', 'Pixels grouped into meaningful spatial objects')

region = slide.shapes.add_shape(1, Inches(0.9), Inches(1.8), Inches(6.6), Inches(4.0))
region.fill.solid(); region.fill.fore_color.rgb = RGBColor(18, 31, 44)
region.line.color.rgb = CYAN
region.text = 'Change mask and connected regions'
region.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
region.text_frame.paragraphs[0].runs[0].font.bold = True

for i, item in enumerate(['Region 0001', 'Region 0112', 'Region 0120']):
    box = slide.shapes.add_shape(1, Inches(8.2), Inches(2.1 + i * 0.9), Inches(3.6), Inches(0.7))
    box.fill.solid(); box.fill.fore_color.rgb = RGBColor(23, 40, 53)
    box.line.color.rgb = CYAN
    tf = box.text_frame; tf.paragraphs[0].text = item; tf.paragraphs[0].runs[0].font.size = Pt(16); tf.paragraphs[0].runs[0].font.bold = True

summary = slide.shapes.add_textbox(Inches(1.0), Inches(5.9), Inches(10.5), Inches(0.7))
summary.text_frame.paragraphs[0].text = '132 Retained Change Regions | Area | Pixel Count | Change Magnitude | Spectral Pattern'
summary.text_frame.paragraphs[0].runs[0].font.size = Pt(18)
summary.text_frame.paragraphs[0].runs[0].font.color.rgb = LIGHT
add_footer(slide)

# Slide 8
slide = prs.slides.add_slide(prs.slide_layouts[6])
apply_bg(slide)
add_title(slide, 'Natural-Language Search', 'The main live demo moment')

search_box = slide.shapes.add_shape(1, Inches(0.9), Inches(1.8), Inches(7.8), Inches(1.1))
search_box.fill.solid(); search_box.fill.fore_color.rgb = RGBColor(16, 30, 39)
search_box.line.color.rgb = CYAN
search_box.text = 'Find regions with strong vegetation-related spectral change'
search_box.text_frame.paragraphs[0].runs[0].font.size = Pt(18)
search_box.text_frame.paragraphs[0].runs[0].font.bold = True

results = slide.shapes.add_shape(1, Inches(0.9), Inches(3.3), Inches(5.6), Inches(2.8))
results.fill.solid(); results.fill.fore_color.rgb = RGBColor(17, 30, 41)
results.line.color.rgb = CYAN
rtf = results.text_frame
for i, name in enumerate(['1. region_0112', '2. region_0001', '3. region_0120', '4. region_0101', '5. region_0008']):
    p = rtf.paragraphs[0] if i == 0 else rtf.add_paragraph()
    p.text = name
    p.runs[0].font.size = Pt(18)
    p.runs[0].font.color.rgb = WHITE

map_box = slide.shapes.add_shape(1, Inches(7.6), Inches(3.3), Inches(4.5), Inches(2.5))
map_box.fill.solid(); map_box.fill.fore_color.rgb = RGBColor(24, 40, 52)
map_box.line.color.rgb = CYAN
map_box.text = 'Retrieved regions\nmap view'
map_box.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
map_box.text_frame.paragraphs[0].runs[0].font.bold = True

note = slide.shapes.add_textbox(Inches(1.0), Inches(6.2), Inches(11.0), Inches(0.5))
note.text_frame.paragraphs[0].text = 'The system searches the region representations and returns the most semantically relevant matches.'
note.text_frame.paragraphs[0].runs[0].font.size = Pt(16)
note.text_frame.paragraphs[0].runs[0].font.color.rgb = LIGHT
add_footer(slide)

# Slide 9
slide = prs.slides.add_slide(prs.slide_layouts[6])
apply_bg(slide)
add_title(slide, 'Scientific Evidence', 'Traceable, measurable, and cautious')

panel = slide.shapes.add_shape(1, Inches(0.9), Inches(1.7), Inches(11.3), Inches(4.5))
panel.fill.solid(); panel.fill.fore_color.rgb = RGBColor(18, 31, 42)
panel.line.color.rgb = CYAN

tf = panel.text_frame
facts = [
    'Region ID: region_0112',
    'Retrieval Rank: 1',
    'Semantic Similarity Score: 0.893452',
    'Area: 18,240 m²',
    'Pixel Count: 4,182',
    'Mean Change Magnitude: 0.72',
    'Spectral Summary: vegetation-related band differences',
    'Reference Date: 2023-06-05 | Moving Date: 2024-06-26'
]
for i, fact in enumerate(facts):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.text = fact
    p.runs[0].font.size = Pt(18)
    p.runs[0].font.color.rgb = WHITE

note = slide.shapes.add_textbox(Inches(1.0), Inches(6.2), Inches(11.0), Inches(0.5))
note.text_frame.paragraphs[0].text = 'This is a cautious spectral interpretation based on measured satellite evidence and region metadata.'
note.text_frame.paragraphs[0].runs[0].font.size = Pt(15)
note.text_frame.paragraphs[0].runs[0].font.color.rgb = LIGHT
add_footer(slide)

# Slide 10
slide = prs.slides.add_slide(prs.slide_layouts[6])
apply_bg(slide)
add_title(slide, 'Scientific Limitations and Impact', 'Responsible, not over-claimed')

left = slide.shapes.add_shape(1, Inches(0.9), Inches(1.8), Inches(5.8), Inches(4.2))
left.fill.solid(); left.fill.fore_color.rgb = RGBColor(26, 40, 50)
left.line.color.rgb = RED
ltf = left.text_frame
for idx, item in enumerate([
    'Semantic retrieval is not ground-truth classification.',
    'Retrieval similarity scores are not probabilities.',
    'Spectral change does not automatically confirm a real-world event.',
    'External ground-truth validation remains necessary.'
]):
    p = ltf.paragraphs[0] if idx == 0 else ltf.add_paragraph()
    p.text = item
    p.runs[0].font.size = Pt(17)
    p.runs[0].font.color.rgb = WHITE

right = slide.shapes.add_shape(1, Inches(7.2), Inches(1.8), Inches(4.8), Inches(4.2))
right.fill.solid(); right.fill.fore_color.rgb = RGBColor(18, 37, 47)
right.line.color.rgb = GREEN
rtf = right.text_frame
for idx, item in enumerate(['Satellite Images', 'Quality-Aware Processing', 'Change Detection', 'Spatial Regions', 'Semantic Search', 'Evidence-Based Results']):
    p = rtf.paragraphs[0] if idx == 0 else rtf.add_paragraph()
    p.text = item
    p.runs[0].font.size = Pt(16)
    p.runs[0].font.color.rgb = WHITE

bottom = slide.shapes.add_textbox(Inches(1.1), Inches(6.2), Inches(11.0), Inches(0.6))
bottom.text_frame.paragraphs[0].text = 'This project converts multi-temporal satellite observations into structured, searchable, and evidence-based change information.'
bottom.text_frame.paragraphs[0].runs[0].font.size = Pt(18)
bottom.text_frame.paragraphs[0].runs[0].font.color.rgb = LIGHT
add_footer(slide)

prs.save(OUT)
print(f'Created presentation: {OUT}')
