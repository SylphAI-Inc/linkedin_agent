from adalflow.core.func_tool import FunctionTool
from .web_nav import js as run_js

PROFILE_JS = r"""
(() => {
  // Wait for content to load
  const waitForContent = (maxAttempts = 10) => {
    for (let i = 0; i < maxAttempts; i++) {
      const sections = document.querySelectorAll('section.artdeco-card');
      if (sections.length > 5) return true;
    }
    return false;
  };
  
  waitForContent();
  
  const grab = sel => document.querySelector(sel)?.textContent?.trim() || null;
  
  // Helper to clean duplicated text (e.g., "TextText" -> "Text")
  const cleanDuplicatedText = (text) => {
    if (!text) return text;
    
    // First handle exact duplications like "TextText" -> "Text"
    const half = Math.floor(text.length / 2);
    const firstHalf = text.substring(0, half);
    const secondHalf = text.substring(half);
    
    if (firstHalf === secondHalf && firstHalf.length > 5) {
      text = firstHalf;
    }
    
    // Then handle word-level duplications
    const words = text.split(' ');
    const cleanWords = [];
    let prevWord = '';
    
    for (let word of words) {
      if (word !== prevWord) {
        cleanWords.push(word);
      }
      prevWord = word;
    }
    
    return cleanWords.join(' ').trim();
  };
  
  // Find sections by their visually hidden labels
  const findSectionByLabel = (labelText) => {
    const sections = Array.from(document.querySelectorAll('section.artdeco-card'));
    return sections.find(section => {
      const hiddenLabel = section.querySelector('.visually-hidden');
      return hiddenLabel && hiddenLabel.textContent.toLowerCase().includes(labelText.toLowerCase());
    });
  };
  
  // Extract basic info
  const name = grab('h1, .ph5 h1');
  const headline = grab('.text-body-medium.break-words, .ph5 .text-body-medium');
  const location = grab('.text-body-small.inline.t-black--light.break-words') ||
                  Array.from(document.querySelectorAll('span, div'))
                    .map(x => x.textContent?.trim())
                    .find(t => t && /^[A-Za-z\s,]+,\s*[A-Za-z\s]+$/.test(t) && t.length < 100) || 
                  null;
  
  // Extract About section
  let about = null;
  const aboutSection = findSectionByLabel('about');
  if (aboutSection) {
    const aboutContentDiv = aboutSection.querySelector('.display-flex.ph5.pv3, .display-flex.full-w');
    if (aboutContentDiv) {
      const aboutSpan = aboutContentDiv.querySelector('span');
      about = aboutSpan ? aboutSpan.textContent.trim() : aboutContentDiv.textContent.trim();
    }
    
    if (!about) {
      const textElements = Array.from(aboutSection.querySelectorAll('span, div'))
        .filter(el => {
          const text = el.textContent?.trim() || '';
          return text.length > 100 && 
                 !el.querySelector('button') &&
                 !text.includes('Show all') &&
                 !text.includes('About');
        })
        .sort((a, b) => b.textContent.length - a.textContent.length);
      
      about = textElements[0] ? textElements[0].textContent.trim() : null;
    }
  }
  
  // Extract Experience as array
  let experiences = [];
  const experienceSection = findSectionByLabel('experience');
  if (experienceSection) {
    const experienceItems = Array.from(experienceSection.querySelectorAll('li.artdeco-list__item'))
      .filter(item => {
        const text = item.textContent?.trim() || '';
        return text.length > 100 && !text.includes('Show all experiences') && !text.includes('skills');
      });
    
    experienceItems.forEach((item) => {
      try {
        const flexDiv = item.querySelector('.display-flex.flex-row.justify-space-between');
        if (flexDiv) {
          const lines = flexDiv.textContent.trim().split('\n').map(l => l.trim()).filter(l => l);
          
          if (lines.length >= 2) {
            // Clean title (remove duplication)
            const titleLine = lines[0];
            const title = cleanDuplicatedText(titleLine);
            
            // Clean company info
            const companyLine = lines.find(line => line.includes('·')) || lines[1];
            const company = cleanDuplicatedText(companyLine ? companyLine.split('·')[0].trim() : 'Unknown');
            
            // Find duration
            const timeLine = lines.find(line => 
              line.includes('to') || line.includes('Present') || line.match(/\d{4}/) ||
              line.includes('yr') || line.includes('mo')
            ) || '';
            
            // Find location 
            const locationLine = lines.find(line => 
              line.includes('United States') || line.includes('California') ||
              line.includes('Bay Area') || (line.includes(',') && !line.includes('·'))
            ) || '';
            
            // Get description
            const descLines = lines.filter(line => 
              line !== titleLine && line !== companyLine && 
              line !== timeLine && line !== locationLine && line.length > 20
            );
            
            experiences.push({
              title: title,
              company: company,
              duration: cleanDuplicatedText(timeLine),
              location: cleanDuplicatedText(locationLine),
              description: descLines.join(' ').substring(0, 300) || 'No description provided'
            });
          }
        }
      } catch (e) {
        // Skip problematic entries
      }
    });
  }
  
  // Extract Education as array
  let education = [];
  const educationSection = findSectionByLabel('education');
  if (educationSection) {
    const educationItems = Array.from(educationSection.querySelectorAll('li.artdeco-list__item'))
      .filter(item => {
        const text = item.textContent?.trim() || '';
        return text.length > 50 && !text.includes('skills') && !text.includes('Show all');
      });
    
    educationItems.forEach((item) => {
      try {
        const schoolLink = item.querySelector('a[href*="/company/"]');
        let school = schoolLink ? schoolLink.textContent.trim() : '';
        
        const lines = item.textContent.trim().split('\n').map(l => l.trim()).filter(l => l.length > 0);
        
        if (!school && lines.length > 0) {
          school = lines.find(line => 
            line.includes('University') || line.includes('College') || 
            line.includes('School') || line.includes('Institute')
          ) || lines[0];
        }
        
        const degreeInfo = lines.find(line => 
          line.includes('Bachelor') || line.includes('Master') || 
          line.includes('BS,') || line.includes('MS,') || 
          line.includes('PhD') || line.includes('Diploma')
        ) || '';
        
        const yearInfo = lines.find(line => line.match(/\b20\d{2}\b/)) || '';
        
        education.push({
          school: cleanDuplicatedText(school),
          degree: cleanDuplicatedText(degreeInfo),
          year: cleanDuplicatedText(yearInfo)
        });
      } catch (e) {
        // Skip problematic entries
      }
    });
  }
  
  // Extract Skills 
  let skills = [];
  const skillsSection = findSectionByLabel('skills');
  if (skillsSection) {
    const skillElements = Array.from(skillsSection.querySelectorAll('.visually-hidden'))
      .map(el => el.textContent.trim())
      .filter(skill => 
        skill.length > 1 && skill.length < 50 && 
        !skill.includes('Skills') && !skill.includes('endorsement') &&
        !skill.includes('Endorsed') && skill !== '1' &&
        !skill.includes('Show all') && !skill.includes('Endorse')
      );
    
    skills = [...new Set(skillElements)].slice(0, 15);
  }
  
  return {
    name,
    headline,
    about,
    experiences,
    education,
    skills,
    location,
    url: window.location.href,
    extraction_timestamp: new Date().toISOString(),
    data_quality: {
      has_name: !!name,
      has_headline: !!headline,
      has_about: !!about && about.length > 50,
      experience_count: experiences.length,
      education_count: education.length,
      skills_count: skills.length,
      has_location: !!location,
      total_score: [!!name, !!headline, !!about && about.length > 50, 
                   experiences.length > 0, education.length > 0, !!location].filter(x => x).length
    }
  };
})()
"""


def extract_profile() -> dict:
  return run_js(PROFILE_JS) or {}


ExtractProfileTool = FunctionTool(fn=extract_profile)
