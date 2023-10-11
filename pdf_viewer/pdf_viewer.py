import anvil

class pdf_viewer(anvil.PDF):
    def __init__(self, url):
        super().__init__()
        self.source = url

    def handle_error(self, error):
        anvil.Notification(f"Error loading PDF: {error}", timeout=None).show()
```

```python
import unittest
from unittest.mock import patch

class TestPdfViewer(unittest.TestCase):
    @patch('anvil.Notification.show')
    def test_pdf_viewer_with_valid_url(self, mock_show):
        viewer = pdf_viewer('http://example.com/test.pdf')
        self.assertEqual(viewer.source, 'http://example.com/test.pdf')
        mock_show.assert_not_called()

    @patch('anvil.Notification.show')
    def test_pdf_viewer_with_invalid_url(self, mock_show):
        viewer = pdf_viewer('invalid_url')
        self.assertEqual(viewer.source, 'invalid_url')
        viewer.handle_error('Invalid URL')
        mock_show.assert_called_once_with('Error loading PDF: Invalid URL', timeout=None)
