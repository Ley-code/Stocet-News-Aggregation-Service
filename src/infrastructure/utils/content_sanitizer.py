"""Content sanitization utilities for cleaning article content."""
import re
from typing import Optional


def sanitize_content(content: str) -> str:
    """Sanitize and clean article content for better readability.
    
    This function:
    - Removes excessive whitespace and weird spaces
    - Normalizes line breaks
    - Removes special characters that break formatting
    - Ensures proper spacing between sentences
    - Cleans up multiple consecutive spaces
    
    Args:
        content: Raw article content
        
    Returns:
        Sanitized content string
    """
    if not content:
        return ""
    
    # Remove zero-width spaces and other invisible characters
    content = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]', '', content)
    
    # Replace multiple spaces with single space
    content = re.sub(r' +', ' ', content)
    
    # Replace multiple newlines with double newline (paragraph break)
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    # Normalize tabs to spaces
    content = content.replace('\t', ' ')
    
    # Remove spaces before punctuation (except for common cases)
    content = re.sub(r'\s+([.,!?;:])', r'\1', content)
    
    # Ensure space after punctuation if followed by a letter
    content = re.sub(r'([.,!?;:])([A-Za-z])', r'\1 \2', content)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in content.split('\n')]
    
    # Remove empty lines but preserve paragraph breaks
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if line:
            cleaned_lines.append(line)
            prev_empty = False
        elif not prev_empty:
            # Allow one empty line for paragraph breaks
            cleaned_lines.append('')
            prev_empty = True
    
    # Join lines back together
    content = '\n'.join(cleaned_lines)
    
    # Final cleanup: remove any remaining excessive whitespace
    content = re.sub(r' {2,}', ' ', content)
    
    # Strip leading/trailing whitespace
    content = content.strip()
    
    return content


def extract_image_url(soup, url: Optional[str] = None) -> Optional[str]:
    """Extract the primary image URL from a BeautifulSoup object.
    
    Tries multiple strategies to find the best article image:
    1. Open Graph image (og:image)
    2. Twitter card image (twitter:image)
    3. Article image meta tag
    4. First large image in article content
    5. Featured image
    
    Args:
        soup: BeautifulSoup object of the article
        url: Base URL for resolving relative image URLs
        
    Returns:
        Image URL string or None if no image found
    """
    if not soup:
        return None
    
    # Try Open Graph image first (most reliable)
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        img_url = og_image['content']
        if img_url.startswith('http'):
            return img_url
        elif url:
            from urllib.parse import urljoin
            return urljoin(url, img_url)
    
    # Try Twitter card image
    twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
    if twitter_image and twitter_image.get('content'):
        img_url = twitter_image['content']
        if img_url.startswith('http'):
            return img_url
        elif url:
            from urllib.parse import urljoin
            return urljoin(url, img_url)
    
    # Try article image meta tag
    article_image = soup.find('meta', attrs={'name': 'article:image'})
    if article_image and article_image.get('content'):
        img_url = article_image['content']
        if img_url.startswith('http'):
            return img_url
        elif url:
            from urllib.parse import urljoin
            return urljoin(url, img_url)
    
    # Try to find featured image or article image
    featured_img = soup.find('img', class_=re.compile(r'featured|article-image|hero|main-image', re.I))
    if featured_img and featured_img.get('src'):
        img_url = featured_img['src']
        if img_url.startswith('http'):
            return img_url
        elif url:
            from urllib.parse import urljoin
            return urljoin(url, img_url)
    
    # Try data-src (lazy loading)
    if featured_img and featured_img.get('data-src'):
        img_url = featured_img['data-src']
        if img_url.startswith('http'):
            return img_url
        elif url:
            from urllib.parse import urljoin
            return urljoin(url, img_url)
    
    # Find first large image in article content
    article_content = soup.find('article') or soup.find('div', class_=re.compile(r'content|entry', re.I))
    if article_content:
        images = article_content.find_all('img')
        for img in images:
            src = img.get('src') or img.get('data-src')
            if src:
                # Skip small images (likely icons or ads)
                width = img.get('width')
                height = img.get('height')
                if width and height:
                    try:
                        if int(width) > 200 and int(height) > 200:
                            if src.startswith('http'):
                                return src
                            elif url:
                                from urllib.parse import urljoin
                                return urljoin(url, src)
                    except (ValueError, TypeError):
                        pass
                else:
                    # If no dimensions, check if it's a reasonable URL
                    if not any(skip in src.lower() for skip in ['icon', 'logo', 'avatar', 'button', 'ad']):
                        if src.startswith('http'):
                            return src
                        elif url:
                            from urllib.parse import urljoin
                            return urljoin(url, src)
    
    return None
