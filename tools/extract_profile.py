from adalflow.core.func_tool import FunctionTool
from .web_nav import js as run_js

PROFILE_JS = r"""
(() => {
  // Wait for content to load
  const waitForContent = (maxAttempts = 10) => {
    for (let i = 0; i < maxAttempts; i++) {
      const sections = document.querySelectorAll('section.artdeco-card');
      if (sections.length > 5) return true;
      // Synchronous wait - not ideal but necessary for extraction
    }
    return false;
  };
  
  waitForContent();
  
  const grab = sel => document.querySelector(sel)?.textContent?.trim() || null;
  
  // Extract content from specific sections more intelligently
  const extractSectionContent = (sectionKeyword, fallbackSelector = null) => {
    // Find all sections
    const sections = Array.from(document.querySelectorAll('section.artdeco-card'));
    
    // Find section with the keyword in its text
    const targetSection = sections.find(section => {
      const text = section.textContent.toLowerCase();
      return text.includes(sectionKeyword.toLowerCase()) && 
             !text.includes('loading') && 
             !text.includes('see more results');
    });
    
    if (!targetSection) return null;
    
    // Try multiple strategies to extract clean content
    const strategies = [
      // Strategy 1: Look for content after the heading
      () => {
        const heading = targetSection.querySelector('h2, h3, .pvs-header__title');
        if (heading) {
          const content = [];
          let sibling = heading.parentElement?.nextElementSibling;
          while (sibling && content.length < 5) {
            const text = sibling.textContent?.trim();
            if (text && text.length > 20 && !text.includes('Show all')) {
              content.push(text);
            }
            sibling = sibling.nextElementSibling;
          }
          return content.join('\\n\\n').substring(0, 1000);
        }
        return null;
      },
      
      // Strategy 2: Look for paragraph-like content
      () => {
        const textElements = Array.from(targetSection.querySelectorAll('span, div, p'))
          .filter(el => {
            const text = el.textContent?.trim() || '';
            return text.length > 50 && 
                   text.length < 2000 &&
                   !el.querySelector('button, a, input') &&
                   !text.includes('Show all') &&
                   !text.toLowerCase().includes(sectionKeyword.toLowerCase());
          })
          .sort((a, b) => b.textContent.length - a.textContent.length);
        
        return textElements[0]?.textContent?.trim()?.substring(0, 1000) || null;
      },
      
      // Strategy 3: Fallback to section text but clean it
      () => {
        const text = targetSection.textContent.trim();
        const lines = text.split('\\n').filter(line => {
          const clean = line.trim();
          return clean.length > 10 && 
                 !clean.toLowerCase().includes(sectionKeyword.toLowerCase()) &&
                 !clean.includes('Show all') &&
                 !clean.includes('see more') &&
                 !clean.includes('•') &&
                 !/^[0-9]+$/.test(clean);
        });
        return lines.slice(0, 3).join(' ').substring(0, 1000);
      }
    ];
    
    for (let strategy of strategies) {
      try {
        const result = strategy();
        if (result && result.length > 30) {
          return result;
        }
      } catch (e) {
        continue;
      }
    }
    
    return null;
  };
  
  // Extract basic info using proven selectors from DOM analysis
  const name = grab('h1, .ph5 h1');
  const headline = grab('.text-body-medium.break-words, .ph5 .text-body-medium');
  
  // Extract section content using improved method
  const about = extractSectionContent('about');
  const experience = extractSectionContent('experience'); 
  const education = extractSectionContent('education');
  
  // Extract location more precisely
  const location = grab('.text-body-small.inline.t-black--light.break-words') ||
                  Array.from(document.querySelectorAll('span, div'))
                    .map(x => x.textContent?.trim())
                    .find(t => t && /^[A-Za-z\s,]+,\s*[A-Za-z\s]+$/.test(t) && t.length < 100) || 
                  null;
  
  return { 
    name, 
    headline, 
    about, 
    experience, 
    education, 
    location, 
    url: window.location.href 
  };
})()
"""


def extract_profile() -> dict:
  return run_js(PROFILE_JS) or {}


ExtractProfileTool = FunctionTool(fn=extract_profile)
