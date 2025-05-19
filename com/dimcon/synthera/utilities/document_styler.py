from docx.shared import Pt
from docx.enum.style import WD_STYLE_TYPE
import logging

logger = logging.getLogger(__name__)

class DocumentStyler:
    @staticmethod
    def apply_styles(document):
        """
        Apply all document-wide styles including font sizes and names.
        """
        try:
            styles = document.styles

            # Normal Body Text
            normal_style = styles['Normal']
            normal_style.font.name = 'Times New Roman'
            normal_style.font.size = Pt(12)

            # Heading 1
            heading1 = styles['Heading 1']
            heading1.font.name = 'Times New Roman'
            heading1.font.size = Pt(16)

            # TOC Heading
            if 'TOC Heading' in styles:
                toc_heading = styles['TOC Heading']
            else:
                toc_heading = styles.add_style('TOC Heading', WD_STYLE_TYPE.PARAGRAPH)
            toc_heading.font.name = 'Times New Roman'
            toc_heading.font.size = Pt(14)
            toc_heading.font.bold = True

            # TOC Entry
            if 'TOC Entry' not in styles:
                toc_entry = styles.add_style('TOC Entry', WD_STYLE_TYPE.PARAGRAPH)
                toc_entry.font.name = 'Times New Roman'
                toc_entry.font.size = Pt(12)

            # TOC SubEntry
            if 'TOC SubEntry' not in styles:
                toc_subentry = styles.add_style('TOC SubEntry', WD_STYLE_TYPE.PARAGRAPH)
                toc_subentry.font.name = 'Times New Roman'
                toc_subentry.font.size = Pt(11)
                toc_subentry.font.italic = True

            logger.info("Document styles successfully applied.")
        except Exception as e:
            logger.error(f"Failed to apply styles: {e}", exc_info=True)
            raise
