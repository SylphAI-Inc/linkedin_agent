"""
Enhanced LinkedIn Profile Extraction using AdalFlow DataClass and Output Parsers
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from adalflow.core import Generator
from adalflow.components.output_parsers.dataclass_parser import DataClassParser
from adalflow.components.model_client import OpenAIClient
from adalflow.core.func_tool import FunctionTool

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.linkedin_profile import LinkedInProfile, Experience, Education, Skill
from .web_nav import js as run_js, go, wait
from config import get_model_kwargs


# AI Prompt for parsing raw profile data
PROFILE_ANALYSIS_PROMPT = r"""
You are a LinkedIn profile data parser. Parse the following raw LinkedIn profile data into a structured format.

Raw Profile Data:
{raw_data}

Instructions:
- Extract all available information accurately
- Structure the data according to the provided format
- If information is missing or unclear, use appropriate defaults
- Ensure all fields are properly typed and formatted

{format_instructions}
"""

# Comprehensive JavaScript for deep profile extraction
COMPREHENSIVE_PROFILE_JS = r"""
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
  
  // Find sections by their visually hidden labels (confirmed consistent pattern)
  const findSectionByLabel = (labelText) => {
    const sections = Array.from(document.querySelectorAll('section.artdeco-card'));
    return sections.find(section => {
      const hiddenLabel = section.querySelector('.visually-hidden');
      return hiddenLabel && hiddenLabel.textContent.toLowerCase().includes(labelText.toLowerCase());
    });
  };
  
  // Extract basic info using proven selectors
  const name = grab('h1, .ph5 h1');
  const headline = grab('.text-body-medium.break-words, .ph5 .text-body-medium');
  const location = grab('.text-body-small.inline.t-black--light.break-words') ||
                  Array.from(document.querySelectorAll('span, div'))
                    .map(x => x.textContent?.trim())
                    .find(t => t && /^[A-Za-z\s,]+,\s*[A-Za-z\s]+$/.test(t) && t.length < 100) || 
                  null;
  
  // Extract About section - uses .ph5 .pv3 containers (from analysis)
  let about = null;
  const aboutSection = findSectionByLabel('about');
  if (aboutSection) {
    // Based on analysis: About section has content in .display-flex, .ph5, .pv3
    const contentContainers = aboutSection.querySelectorAll('.display-flex span, .ph5 span, .pv3 span');
    const aboutText = Array.from(contentContainers)
      .map(el => el.textContent?.trim())
      .find(text => text && text.length > 100 && !text.includes('About'));
    
    about = aboutText || null;
  }
  
  // ---------- helpers ----------
  const qa = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const q  = (sel, root = document) => root.querySelector(sel);
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const isHidden = el =>
    !el || el.closest('.visually-hidden,[aria-hidden="true"]') || el.getAttribute?.('aria-hidden') === 'true';

  // Prefer LinkedIn’s duplicated visible text in aria-hidden nodes; else strip hidden nodes
  const getVisibleText = (el) => {
    if (!el) return '';
    const ariaTexts = qa('span[aria-hidden="true"]', el)
      .filter(s => !isHidden(s))
      .map(s => norm(s.textContent))
      .filter(Boolean);
    if (ariaTexts.length) return ariaTexts.join(' ');
    const clone = el.cloneNode(true);
    qa('.visually-hidden,[aria-hidden="true"]', clone).forEach(n => n.remove());
    return norm(clone.textContent);
  };

  const expandSeeMore = (root) => {
    qa('button.inline-show-more-text__button', root).forEach(b => { try { b.click(); } catch {} });
  };

  const findSectionByHeading = (label) => {
    return qa('section.artdeco-card').find(sec => {
      const h2 = q('h2.pvs-header__title', sec);
      return h2 && getVisibleText(h2).toLowerCase().includes(label.toLowerCase());
    }) || null;
  };

  const DATE_RX = /([A-Za-z]{3,9}\s\d{4})\s*-\s*(Present|[A-Za-z]{3,9}\s\d{4})(?:\s*·\s*([\d\s\w]+))?/i;
  const looksLikeLocation = t =>
    /\b(remote|on[-\s]?site|hybrid)\b/i.test(t) ||
    /[A-Za-z]+,\s*[A-Za-z]+/.test(t) ||
    /(United\sStates|Canada|China|UK|Singapore|Australia)/i.test(t);

  // ---------- EXPERIENCE ----------
  const scrapeExperience = (section) => {
    expandSeeMore(section);

    const out = [];
    const blocks = qa('[data-view-name="profile-component-entity"]', section);

    const norm = s => (s || '').replace(/\s+/g, ' ').trim();

    for (const item of blocks) {
      // Title: bold line → aria-hidden text only
      const title =
        norm(q('.t-bold span[aria-hidden="true"]', item)?.textContent) ||
        norm(q('.hoverable-link-text.t-bold span[aria-hidden="true"]', item)?.textContent) ||
        'Unknown Title';

      // The three t-14 lines (company, dates, location) in order; aria-hidden text only
      const metaSpans = qa('.t-14.t-normal span[aria-hidden="true"], .t-14.t-normal.t-black--light span[aria-hidden="true"]', item);
      const company   = norm(metaSpans?.[0]?.textContent) || '';
      const dateRaw   = norm(q('.pvs-entity__caption-wrapper[aria-hidden="true"]', item)?.textContent) // often the dates live here
                      || norm(metaSpans?.[1]?.textContent) || '';
      const location  = norm(metaSpans?.[2]?.textContent) || '';

      // Dates/duration parse
      const DATE_RX = /([A-Za-z]{3,9}\s\d{4})\s*-\s*(Present|[A-Za-z]{3,9}\s\d{4})(?:\s*·\s*([\d\s\w]+))?/i;
      let start_date = '', end_date = '', duration = '';
      const m = DATE_RX.exec(dateRaw);
      if (m) {
        start_date = m[1] || '';
        end_date   = m[2] || '';
        duration   = m[3] || '';
      }

      // Bullets: read only aria-hidden text; reconstruct line breaks
      let bullets = [];
      const textHost = q('.inline-show-more-text--is-expanded, .inline-show-more-text--is-collapsed', item);
      if (textHost) {
        const nodes = qa('[aria-hidden="true"]', textHost); // only aria-hidden text nodes
        const joined = norm(nodes.map(n => n.textContent || '').join('\n'));
        bullets = joined
          .split(/\n+/)
          .map(s => norm(s.replace(/^[-•]\s*/, '')))
          .filter(s => s && s.length > 3 && !DATE_RX.test(s));
      }

      const company_linkedin = q('a[href*="/company/"]', item)?.getAttribute('href') || '';
      const logo_url = q('.pvs-entity__image img, img[alt$="logo"]', item)?.getAttribute('src') || '';
      const company_website =
        q('.pvs-thumbnail__wrapper ~ a[href^="http"]', item)?.getAttribute('href') ||
        q('a[href^="http"]:not([href*="linkedin.com"])', item)?.getAttribute('href') || '';

      const record = {
        title: title.replace(/(.+)\1+/, '$1'),
        company: (company || 'Unknown Company').replace(/(.+)\1+/, '$1').replace(/\s*·\s*Full-time.*/i, ''),
        start_date,
        end_date,
        duration,
        location,
        bullets,
        company_linkedin,
        company_website,
        logo_url
      };

      if (record.title === 'Unknown Title' && record.company === 'Unknown Company') continue;
      out.push(record);
    }

    return out;
  };

  // ---------- EDUCATION ----------
  const scrapeEducation = (section) => {
    expandSeeMore(section);
    const blocks = qa('[data-view-name="profile-component-entity"]', section);
    const out = [];

    // Regex: range or single date (e.g., "Sep 2021 - Jun 2025 · 4 yrs" OR "Jun 2027")
    const RANGE_RX  = /([A-Za-z]{3,9}\s?\d{4}|\d{4})\s*-\s*(Present|[A-Za-z]{3,9}\s?\d{4}|\d{4})(?:\s*·\s*([\d\s\w]+))?/i;
    const SINGLE_RX = /^(?:[A-Za-z]{3,9}\s)?\d{4}$/i;

    const norm = s => (s || '').replace(/\s+/g, ' ').trim();

    for (const item of blocks) {
      // School: bold line → aria-hidden text only
      const schoolLink = q('a[href*="/school/"], a[href*="/company/"]', item);
      const school =
        norm(q('.t-bold span[aria-hidden="true"]', item)?.textContent) ||
        norm(q('.t-bold', item)?.textContent) ||
        norm(schoolLink?.textContent) ||
        'Unknown School';

      // Degree/program: first t-14 line that is NOT the caption wrapper
      const degreeSpan = qa('.t-14.t-normal span[aria-hidden="true"]', item)
        .find(s => !s.closest('.pvs-entity__caption-wrapper'));
      const degree = norm(degreeSpan?.textContent) || '';

      // Date text lives in the caption wrapper (and is aria-hidden)
      const dateText =
        norm(q('.pvs-entity__caption-wrapper[aria-hidden="true"]', item)?.textContent) || '';

      let start_date = '', end_date = '', duration = '';

      if (dateText) {
        const mRange = RANGE_RX.exec(dateText);
        if (mRange) {
          start_date = mRange[1] || '';
          end_date   = mRange[2] || '';
          duration   = mRange[3] || '';
        } else if (SINGLE_RX.test(dateText)) {
          // Single graduation date (e.g., "Jun 2027" or "2027")
          end_date = dateText;
        }
      }

      const logo_url = q('.pvs-entity__image img, img[alt$="logo"]', item)?.getAttribute('src') || '';
      const school_linkedin = schoolLink?.getAttribute('href') || '';

      out.push({
        school: school.replace(/(.+)\1+/, '$1'),
        degree: degree.replace(/(.+)\1+/, '$1'),
        start_date,
        end_date,
        duration,
        logo_url,
        school_linkedin
      });
    }

    return out;
  };
  
  const findSectionByAnchorId = (id) => {
    const anchor = document.querySelector(`div#${id}.pv-profile-card__anchor`);
    return anchor ? anchor.closest('section.artdeco-card') : null;
  };

  // Fallback to the heading text if the anchor isn’t present yet
  const findSection = (anchorId, headingLabel) =>
    findSectionByAnchorId(anchorId) || findSectionByHeading(headingLabel);

  // Use these instead of findSectionByHeading directly:
  const experienceSection = findSection('experience', 'Experience');
  const educationSection  = findSection('education',  'Education');

  const experiences = experienceSection ? scrapeExperience(experienceSection) : [];
  const education   = educationSection  ? scrapeEducation(educationSection)  : [];

  // ---------- CERTIFICATIONS ----------

  const scrapeCertifications = (section) => {
    expandSeeMore(section);
    const blocks = qa('[data-view-name="profile-component-entity"]', section);
    const out = [];

    const norm = s => (s || '').replace(/\s+/g, ' ').trim();

    // e.g., "Issued Sep 2014 · Expires Sep 2016" OR "Issued Sep 2014"
    const ISSUED_RX = /Issued\s+([A-Za-z]{3,9}\s?\d{4}|\d{4})(?:\s*·\s*Expires\s+([A-Za-z]{3,9}\s?\d{4}|\d{4}))?/i;

    for (const item of blocks) {
      // Title (cert name)
      const name =
        norm(q('.t-bold span[aria-hidden="true"]', item)?.textContent) ||
        'Unknown Certification';

      // Issuer: first .t-14 line (aria-hidden)
      const issuer =
        norm(q('.t-14.t-normal span[aria-hidden="true"]', item)?.textContent) || '';

      // Issued/Expires: caption wrapper (aria-hidden)
      const issuedRaw =
        norm(q('.pvs-entity__caption-wrapper[aria-hidden="true"]', item)?.textContent) || '';
      let issued_on = '', expires_on = '';
      const m = ISSUED_RX.exec(issuedRaw);
      if (m) {
        issued_on  = m[1] || '';
        expires_on = m[2] || '';
      }

      // Credential ID: look for a black--light t-14 line that starts with "Credential ID"
      const idSpan = qa('.t-14.t-normal.t-black--light span[aria-hidden="true"]', item)
        .find(s => /Credential ID/i.test(s.textContent || ''));
      const credential_id = idSpan
        ? norm((idSpan.textContent || '').replace(/^\s*Credential ID\s*/i, ''))
        : '';

      // Links & logo
      const issuer_linkedin = q('a[href*="/company/"]', item)?.getAttribute('href') || '';
      const logo_url = q('.pvs-entity__image img, img[alt$="logo"]', item)?.getAttribute('src') || '';
      // Prefer explicit credential link; fallback to any non-LinkedIn http link in the item
      const credential_url =
        q('a.optional-action-target-wrapper[href^="http"]:not([href*="linkedin.com"])', item)?.getAttribute('href') ||
        q('.pvs-entity__sub-components a[href^="http"]:not([href*="linkedin.com"])', item)?.getAttribute('href') ||
        q('a[href^="http"]:not([href*="linkedin.com"])', item)?.getAttribute('href') || '';

      out.push({
        name,
        issuer,
        issued_on,
        expires_on,
        credential_id,
        credential_url,
        issuer_linkedin,
        logo_url
      });
    }

    return out;
  };

  const certsSection = findSectionByAnchorId('licenses_and_certifications');
  const certifications = certsSection ? scrapeCertifications(certsSection) : [];

  // Extract Skills - uses .pvs-entity__sub-components .artdeco-list__item (from analysis)
  let skills = [];
  const skillsSection = findSectionByLabel('skills');
  if (skillsSection) {
    // Skills are often in .visually-hidden elements or specific spans
    const skillSpans = skillsSection.querySelectorAll('span');
    const skillTexts = Array.from(skillSpans)
      .map(span => span.textContent.trim())
      .filter(text => 
        text.length > 2 && text.length < 50 &&
        !text.includes('Skills') && !text.includes('endorsement') &&
        !text.includes('Show all') && !text.match(/^\d+$/)
      );
    
    // Remove duplicates and take top skills, filter out endorsement noise
    skills = [...new Set(skillTexts)]
      .filter(skill => 
        !skill.includes('Endorsed') && 
        !skill.includes('Endorse') && 
        !skill.includes('months') &&
        skill.length > 2
      )
      .slice(0, 15);
  }
  
  // ---------- LANGUAGES ----------
  const scrapeLanguages = (section) => {
    expandSeeMore(section);
    const blocks = qa('[data-view-name="profile-component-entity"]', section);
    const out = [];
    const norm = s => (s || '').replace(/\s+/g, ' ').trim();

    for (const item of blocks) {
      const name =
        norm(q('.t-bold span[aria-hidden="true"]', item)?.textContent) ||
        'Unknown Language';

      // Proficiency lives in caption wrapper aria-hidden
      const proficiency =
        norm(q('.pvs-entity__caption-wrapper[aria-hidden="true"]', item)?.textContent) || '';

      out.push({ name, proficiency });
    }

    // Optional: capture “see all” link if you want to follow to the detail page
    const seeAll =
      q('#navigation-index-see-all-languages', section)?.getAttribute('href') || '';
    return { items: out, see_all_url: seeAll };
  };

  // usage:
  const languagesSection = document.querySelector('div#languages.pv-profile-card__anchor')
    ?.closest('section.artdeco-card');
  const languages = languagesSection ? scrapeLanguages(languagesSection) : { items: [], see_all_url: '' };

  return {
    name,
    headline,
    about,
    experiences,
    education,
    certifications,
    skills,
    languages,
    location,
    url: window.location.href,
    extraction_timestamp: new Date().toISOString(),
    extraction_method: 'dom_based_consistent_selectors',
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


class ProfileExtractor:
    """Enhanced LinkedIn profile extractor with AI parsing"""
    
    def __init__(self):
        self.client = OpenAIClient()
        self.parser = DataClassParser(
            data_class=LinkedInProfile,
            return_data_class=True,
            format_type="json"
        )
        self.generator = Generator(
            model_client=self.client,
            model_kwargs=get_model_kwargs(),
            template=PROFILE_ANALYSIS_PROMPT,
            output_processors=self.parser
        )
    
    def navigate_to_profile(self, profile_url: str) -> bool:
        """Navigate to a specific LinkedIn profile"""
        try:
            print(f"Navigating to profile: {profile_url}")
            go(profile_url)
            
            # Wait for profile to load
            if wait('main h1', timeout=10.0):
                print("Profile loaded successfully")
                return True
            else:
                print("Profile failed to load")
                return False
                
        except Exception as e:
            print(f"Navigation error: {e}")
            return False
    
    def extract_raw_profile_data(self) -> Dict[str, Any]:
        """Extract raw profile data using JavaScript"""
        try:
            print("Extracting raw profile data...")
            raw_data = run_js(COMPREHENSIVE_PROFILE_JS)
            
            if raw_data and isinstance(raw_data, dict):
                print(f"Raw data extracted: {raw_data.get('name', 'Unknown')}")
                return raw_data
            else:
                print("No raw data extracted")
                return {}
                
        except Exception as e:
            print(f"Extraction error: {e}")
            return {}
    
    def parse_with_ai(self, raw_data: Dict[str, Any]) -> Optional[LinkedInProfile]:
        """Use AI to parse and structure the raw profile data"""
        try:
            print("Parsing raw data with AI...")
            
            # Prepare the data for the AI prompt
            raw_json = json.dumps(raw_data, indent=2)
            
            # Generate structured output using direct call with prompt_kwargs
            response = self.generator(
                prompt_kwargs={
                    "raw_data": raw_json,
                    "format_instructions": self.parser.get_output_format_str()
                }
            )
            
            if response and hasattr(response, 'data'):
                profile = response.data
                print(f"AI parsing successful: {profile.name}")
                return profile
            else:
                print("AI parsing failed - no structured data returned")
                return None
                
        except Exception as e:
            print(f"AI parsing error: {e}")
            return None
    
    def fallback_parse(self, raw_data: Dict[str, Any]) -> LinkedInProfile:
        """Fallback parsing without AI if needed"""
        try:
            print("Using fallback parsing...")
            
            # Extract experiences
            experiences = []
            if raw_data.get('experience'):
                for exp in raw_data['experience']:
                    if isinstance(exp, dict):
                        experiences.append(Experience(
                            title=exp.get('title', ''),
                            company=exp.get('company', ''),
                            duration=exp.get('duration', ''),
                            location=exp.get('location'),
                            description=exp.get('description')
                        ))
            
            # Extract education
            education = []
            if raw_data.get('education'):
                for edu in raw_data['education']:
                    if isinstance(edu, dict):
                        education.append(Education(
                            institution=edu.get('institution', ''),
                            degree=edu.get('degree'),
                            duration=edu.get('duration')
                        ))
            
            # Extract skills
            skills = []
            if raw_data.get('skills'):
                for skill in raw_data['skills']:
                    if isinstance(skill, dict):
                        skills.append(Skill(
                            name=skill.get('name', ''),
                            endorsements=skill.get('endorsements', 0)
                        ))
            
            # Basic industry keywords extraction
            industry_keywords = []
            text_to_analyze = f"{raw_data.get('headline', '')} {raw_data.get('about', '')}"
            common_keywords = ['software', 'engineering', 'product', 'management', 'data', 'marketing', 
                             'sales', 'design', 'analytics', 'AI', 'machine learning', 'cloud']
            
            for keyword in common_keywords:
                if keyword.lower() in text_to_analyze.lower():
                    industry_keywords.append(keyword)
            
            # Calculate completeness score
            completeness_score = self._calculate_completeness(raw_data)
            
            profile = LinkedInProfile(
                name=raw_data.get('name', ''),
                headline=raw_data.get('headline', ''),
                location=raw_data.get('location'),
                about=raw_data.get('about'),
                experience=experiences,
                education=education,
                skills=skills,
                linkedin_url=raw_data.get('linkedin_url'),
                total_experience_years=raw_data.get('total_experience_years'),
                current_company=raw_data.get('current_company'),
                current_title=raw_data.get('current_title'),
                industry_keywords=industry_keywords,
                extraction_timestamp=raw_data.get('extraction_timestamp'),
                data_completeness_score=completeness_score
            )
            
            print(f"Fallback parsing successful: {profile.name}")
            return profile
            
        except Exception as e:
            print(f"Fallback parsing error: {e}")
            # Return minimal profile
            return LinkedInProfile(
                name=raw_data.get('name', 'Unknown'),
                headline=raw_data.get('headline', ''),
                linkedin_url=raw_data.get('linkedin_url'),
                extraction_timestamp=raw_data.get('extraction_timestamp'),
                data_completeness_score=0.1
            )
    
    def _calculate_completeness(self, raw_data: Dict[str, Any]) -> float:
        """Calculate how complete the extracted data is"""
        fields_to_check = [
            ('name', 0.2),           # 20% - essential
            ('headline', 0.15),      # 15% - very important  
            ('about', 0.15),         # 15% - very important
            ('experience', 0.25),    # 25% - critical
            ('education', 0.1),      # 10% - important
            ('skills', 0.1),         # 10% - nice to have
            ('location', 0.05),      # 5% - minor
        ]
        
        score = 0.0
        for field, weight in fields_to_check:
            value = raw_data.get(field)
            if value:
                if isinstance(value, list) and len(value) > 0:
                    score += weight
                elif isinstance(value, str) and value.strip():
                    score += weight
                elif value:  # other truthy values
                    score += weight
        
        return min(score, 1.0)
    
    def extract_complete_profile(self, profile_url: str) -> Optional[LinkedInProfile]:
        """Complete profile extraction workflow"""
        print(f"Starting complete profile extraction for: {profile_url}")
        
        # Step 1: Navigate to profile
        if not self.navigate_to_profile(profile_url):
            return None
        
        # Step 2: Extract raw data
        raw_data = self.extract_raw_profile_data()
        if not raw_data:
            return None
        
        # Step 3: Parse with AI (with fallback)
        profile = self.parse_with_ai(raw_data)
        if not profile:
            profile = self.fallback_parse(raw_data)
        
        print(f"Profile extraction complete: {profile.name} (completeness: {profile.data_completeness_score:.2f})")
        return profile


# Global extractor instance (created on demand)
_extractor = None

def get_global_extractor():
    """Get or create global extractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = ProfileExtractor()
    return _extractor


def extract_complete_profile(profile_url: str) -> dict:
    """Extract complete LinkedIn profile - function tool wrapper"""
    profile = get_global_extractor().extract_complete_profile(profile_url)
    if profile:
        return profile.to_dict()
    else:
        return {"error": "Failed to extract profile", "url": profile_url}


def extract_current_profile() -> dict:
    """Extract profile from current page - function tool wrapper"""
    raw_data = get_global_extractor().extract_raw_profile_data()
    if raw_data:
        profile = get_global_extractor().parse_with_ai(raw_data)
        if not profile:
            profile = get_global_extractor().fallback_parse(raw_data)
        return profile.to_dict()
    else:
        return {"error": "Failed to extract current profile"}


# Function tools for agent
# ExtractCompleteProfileTool = FunctionTool(fn=extract_complete_profile)
ExtractCurrentProfileTool = FunctionTool(fn=extract_current_profile)