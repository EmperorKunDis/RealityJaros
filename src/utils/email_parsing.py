import re
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import html

logger = logging.getLogger(__name__)

class EmailParser:
    """
    Advanced email parsing utilities
    Handles Gmail API message format and content extraction
    """
    
    @staticmethod
    def extract_message_data(gmail_message: Dict) -> Dict:
        """
        Extract structured data from Gmail API message
        
        Args:
            gmail_message: Raw Gmail API message response
            
        Returns:
            Parsed email data dictionary
        """
        try:
            headers = gmail_message.get('payload', {}).get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            
            # Extract basic metadata
            message_data = {
                'message_id': gmail_message.get('id', ''),
                'thread_id': gmail_message.get('threadId', ''),
                'label_ids': gmail_message.get('labelIds', []),
                'snippet': gmail_message.get('snippet', ''),
                'size_estimate': gmail_message.get('sizeEstimate', 0),
                'internal_date': gmail_message.get('internalDate', ''),
                
                # Headers
                'subject': header_dict.get('subject', ''),
                'sender': header_dict.get('from', ''),
                'recipient': header_dict.get('to', ''),
                'cc': header_dict.get('cc', ''),
                'bcc': header_dict.get('bcc', ''),
                'date': header_dict.get('date', ''),
                'message-id': header_dict.get('message-id', ''),
                'in-reply-to': header_dict.get('in-reply-to', ''),
                'references': header_dict.get('references', ''),
            }
            
            # Extract body content
            body_text, body_html = EmailParser._extract_body_content(gmail_message.get('payload', {}))
            message_data['body_text'] = body_text
            message_data['body_html'] = body_html
            
            # Parse datetime
            message_data['sent_datetime'] = EmailParser._parse_email_datetime(
                header_dict.get('date', ''), 
                gmail_message.get('internalDate', '')
            )
            
            # Extract attachments info
            message_data['attachments'] = EmailParser._extract_attachment_info(gmail_message.get('payload', {}))
            message_data['has_attachments'] = len(message_data['attachments']) > 0
            
            return message_data
            
        except Exception as e:
            logger.error(f"Error parsing Gmail message: {e}")
            raise

    @staticmethod
    def _extract_body_content(payload: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text and HTML body content from Gmail payload
        
        Args:
            payload: Gmail message payload
            
        Returns:
            Tuple of (text_body, html_body)
        """
        body_text = None
        body_html = None
        
        try:
            # Handle multipart messages
            if payload.get('mimeType') == 'multipart/alternative' or payload.get('mimeType') == 'multipart/mixed':
                parts = payload.get('parts', [])
                for part in parts:
                    part_mime = part.get('mimeType', '')
                    
                    if part_mime == 'text/plain':
                        body_text = EmailParser._decode_body_data(part.get('body', {}))
                    elif part_mime == 'text/html':
                        body_html = EmailParser._decode_body_data(part.get('body', {}))
                    elif part_mime.startswith('multipart/'):
                        # Recursively handle nested multipart
                        nested_text, nested_html = EmailParser._extract_body_content(part)
                        if nested_text and not body_text:
                            body_text = nested_text
                        if nested_html and not body_html:
                            body_html = nested_html
            
            # Handle single part messages
            elif payload.get('mimeType') == 'text/plain':
                body_text = EmailParser._decode_body_data(payload.get('body', {}))
            elif payload.get('mimeType') == 'text/html':
                body_html = EmailParser._decode_body_data(payload.get('body', {}))
            
            # Clean up HTML content
            if body_html:
                body_html = EmailParser._clean_html_content(body_html)
            
            # If we have HTML but no text, extract text from HTML
            if body_html and not body_text:
                body_text = EmailParser._html_to_text(body_html)
            
            return body_text, body_html
            
        except Exception as e:
            logger.error(f"Error extracting body content: {e}")
            return None, None

    @staticmethod
    def _decode_body_data(body_data: Dict) -> Optional[str]:
        """
        Decode base64 encoded body data
        
        Args:
            body_data: Gmail body data object
            
        Returns:
            Decoded text content
        """
        try:
            data = body_data.get('data', '')
            if not data:
                return None
            
            # Gmail uses URL-safe base64 encoding
            decoded_bytes = base64.urlsafe_b64decode(data + '==')  # Add padding if needed
            return decoded_bytes.decode('utf-8', errors='ignore')
            
        except Exception as e:
            logger.warning(f"Error decoding body data: {e}")
            return None

    @staticmethod
    def _clean_html_content(html_content: str) -> str:
        """
        Clean and normalize HTML content
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned HTML content
        """
        try:
            # Unescape HTML entities
            cleaned = html.unescape(html_content)
            
            # Remove excessive whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
            # Remove common email tracking pixels and invisible content
            cleaned = re.sub(r'<img[^>]*width="1"[^>]*height="1"[^>]*>', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'<div[^>]*style="[^"]*display:\s*none[^"]*"[^>]*>.*?</div>', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
            
            return cleaned.strip()
            
        except Exception as e:
            logger.warning(f"Error cleaning HTML content: {e}")
            return html_content

    @staticmethod
    def _html_to_text(html_content: str) -> str:
        """
        Convert HTML content to plain text
        
        Args:
            html_content: HTML content
            
        Returns:
            Plain text content
        """
        try:
            # Remove script and style elements
            text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
            
            # Convert common HTML elements to text equivalents
            text = re.sub(r'<br[^>]*>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
            text = re.sub(r'</p>', '', text, flags=re.IGNORECASE)
            text = re.sub(r'<div[^>]*>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'</div>', '', text, flags=re.IGNORECASE)
            
            # Remove all remaining HTML tags
            text = re.sub(r'<[^>]*>', '', text)
            
            # Clean up whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines to double
            text = re.sub(r'[ \t]+', ' ', text)      # Multiple spaces to single
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Error converting HTML to text: {e}")
            return html_content

    @staticmethod
    def _parse_email_datetime(date_header: str, internal_date: str) -> Optional[datetime]:
        """
        Parse email date from various formats
        
        Args:
            date_header: Date header from email
            internal_date: Gmail internal date (milliseconds since epoch)
            
        Returns:
            Parsed datetime object
        """
        try:
            # Try Gmail internal date first (most reliable)
            if internal_date:
                timestamp = int(internal_date) / 1000  # Convert from milliseconds
                return datetime.fromtimestamp(timestamp)
            
            # Parse standard email date header
            if date_header:
                # Remove common timezone abbreviations that email.utils can't handle
                cleaned_date = re.sub(r'\s+\([^)]+\)$', '', date_header)
                
                # Try parsing with email.utils
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(cleaned_date)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing email datetime: {e}")
            return None

    @staticmethod
    def _extract_attachment_info(payload: Dict) -> List[Dict]:
        """
        Extract attachment information from email payload
        
        Args:
            payload: Gmail message payload
            
        Returns:
            List of attachment information dictionaries
        """
        attachments = []
        
        try:
            def extract_from_parts(parts):
                for part in parts:
                    if part.get('filename'):
                        attachment_info = {
                            'filename': part.get('filename'),
                            'mime_type': part.get('mimeType'),
                            'size': part.get('body', {}).get('size', 0),
                            'attachment_id': part.get('body', {}).get('attachmentId')
                        }
                        attachments.append(attachment_info)
                    
                    # Recursively check nested parts
                    if part.get('parts'):
                        extract_from_parts(part.get('parts'))
            
            if payload.get('parts'):
                extract_from_parts(payload.get('parts'))
            
            return attachments
            
        except Exception as e:
            logger.warning(f"Error extracting attachment info: {e}")
            return []

    @staticmethod
    def determine_email_direction(sender: str, recipient: str, user_email: str) -> str:
        """
        Determine if email is incoming or outgoing
        
        Args:
            sender: Email sender address
            recipient: Email recipient address
            user_email: User's email address
            
        Returns:
            'incoming' or 'outgoing'
        """
        try:
            user_email = user_email.lower()
            sender = sender.lower()
            
            # Extract email address from "Name <email@domain.com>" format
            sender_match = re.search(r'<([^>]+)>', sender)
            if sender_match:
                sender = sender_match.group(1)
            
            return 'outgoing' if user_email in sender else 'incoming'
            
        except Exception as e:
            logger.warning(f"Error determining email direction: {e}")
            return 'incoming'  # Default to incoming

    @staticmethod
    def extract_email_addresses(address_string: str) -> List[str]:
        """
        Extract clean email addresses from address string
        
        Args:
            address_string: Email address string (may contain names)
            
        Returns:
            List of clean email addresses
        """
        try:
            if not address_string:
                return []
            
            # Split by comma for multiple recipients
            addresses = []
            for addr in address_string.split(','):
                addr = addr.strip()
                
                # Extract email from "Name <email@domain.com>" format
                email_match = re.search(r'<([^>]+)>', addr)
                if email_match:
                    addresses.append(email_match.group(1).strip())
                elif '@' in addr:
                    # Direct email address
                    addresses.append(addr.strip())
            
            return [addr for addr in addresses if addr]
            
        except Exception as e:
            logger.warning(f"Error extracting email addresses: {e}")
            return []