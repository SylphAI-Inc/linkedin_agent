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


# Comprehensive JavaScript for deep profile extraction
COMPREHENSIVE_PROFILE_JS = r"""
(() => {
    console.log("Starting comprehensive profile extraction...");
    
    // Helper functions
    const getText = (selector) => {
        const el = document.querySelector(selector);
        return el ? el.textContent.trim() : null;
    };
    
    const getAllText = (selector) => {
        return Array.from(document.querySelectorAll(selector))
            .map(el => el.textContent.trim())
            .filter(text => text.length > 0);
    };
    
    // Basic profile info
    const name = getText('main h1') || 
                 getText('.pv-text-details__left-panel h1') ||
                 getText('.text-heading-xlarge');
    
    const headline = getText('.text-body-medium.break-words') ||
                     getText('[data-generated-suggestion-target]') ||
                     getText('.pv-text-details__left-panel .text-body-medium');
    
    const location = getText('.text-body-small.inline.t-black--light.break-words') ||
                     getText('.pv-text-details__left-panel .text-body-small');
    
    // About section - more comprehensive extraction
    let about = null;
    const aboutSection = document.querySelector('#about') || 
                        document.querySelector('[data-test-id*="about"]') ||
                        document.querySelector('section.pv-about-section');
    
    if (aboutSection) {
        // Find the expandable content or main text
        const aboutText = aboutSection.querySelector('.pv-shared-text-with-see-more .inline-show-more-text') ||
                         aboutSection.querySelector('.pv-shared-text-with-see-more .full-width') ||
                         aboutSection.querySelector('.display-flex.full-width span[aria-hidden="true"]') ||
                         aboutSection.querySelector('.text-body-medium');
        about = aboutText ? aboutText.textContent.trim() : null;
    }
    
    // Experience extraction
    const experiences = [];
    const expSection = document.querySelector('#experience') || 
                      document.querySelector('[data-test-id*="experience"]');
    
    if (expSection) {
        const expItems = expSection.querySelectorAll('li.artdeco-list__item, .pvs-list__item--line-separated');
        
        expItems.forEach(item => {
            try {
                const titleEl = item.querySelector('.mr1.t-bold span[aria-hidden="true"]') ||
                               item.querySelector('.mr1.hoverable-link-text.t-bold span') ||
                               item.querySelector('div.display-flex.align-items-center.mr1 span');
                
                const companyEl = item.querySelector('.t-14.t-normal span[aria-hidden="true"]') ||
                                 item.querySelector('.pv-entity__secondary-title') ||
                                 item.querySelector('span.t-14.t-normal.break-words span');
                
                const durationEl = item.querySelector('.t-14.t-normal.t-black--light span[aria-hidden="true"]') ||
                                  item.querySelector('.pv-entity__bullet-item-v2');
                
                const locationEl = item.querySelector('.t-14.t-normal.t-black--light span:last-child') ||
                                  item.querySelector('.pv-entity__location span');
                
                const descEl = item.querySelector('.pv-shared-text-with-see-more .inline-show-more-text') ||
                              item.querySelector('.pv-entity__description');
                
                if (titleEl && companyEl) {
                    experiences.push({
                        title: titleEl.textContent.trim(),
                        company: companyEl.textContent.trim(),
                        duration: durationEl ? durationEl.textContent.trim() : null,
                        location: locationEl ? locationEl.textContent.trim() : null,
                        description: descEl ? descEl.textContent.trim() : null
                    });
                }
            } catch (e) {
                console.log("Error extracting experience item:", e);
            }
        });
    }
    
    // Education extraction
    const education = [];
    const eduSection = document.querySelector('#education') ||
                      document.querySelector('[data-test-id*="education"]');
    
    if (eduSection) {
        const eduItems = eduSection.querySelectorAll('li.artdeco-list__item, .pvs-list__item--line-separated');
        
        eduItems.forEach(item => {
            try {
                const schoolEl = item.querySelector('.mr1.t-bold span[aria-hidden="true"]') ||
                                item.querySelector('.pv-entity__school-name');
                
                const degreeEl = item.querySelector('.t-14.t-normal span[aria-hidden="true"]') ||
                               item.querySelector('.pv-entity__degree-name');
                
                const durationEl = item.querySelector('.t-14.t-normal.t-black--light span[aria-hidden="true"]') ||
                                  item.querySelector('.pv-entity__dates');
                
                if (schoolEl) {
                    education.push({
                        institution: schoolEl.textContent.trim(),
                        degree: degreeEl ? degreeEl.textContent.trim() : null,
                        duration: durationEl ? durationEl.textContent.trim() : null
                    });
                }
            } catch (e) {
                console.log("Error extracting education item:", e);
            }
        });
    }
    
    // Skills extraction  
    const skills = [];
    const skillsSection = document.querySelector('#skills') ||
                         document.querySelector('[data-test-id*="skills"]');
    
    if (skillsSection) {
        const skillItems = skillsSection.querySelectorAll('li.artdeco-list__item, .pvs-list__item--line-separated');
        
        skillItems.forEach(item => {
            try {
                const skillEl = item.querySelector('.mr1.t-bold span[aria-hidden="true"]') ||
                               item.querySelector('.pv-skill-category-entity__name-text');
                
                const endorseEl = item.querySelector('.t-14.t-normal.t-black--light') ||
                                 item.querySelector('.pv-skill-category-entity__endorsement-count');
                
                if (skillEl) {
                    const endorsements = endorseEl ? 
                        parseInt(endorseEl.textContent.replace(/\D/g, '')) || 0 : 0;
                    
                    skills.push({
                        name: skillEl.textContent.trim(),
                        endorsements: endorsements
                    });
                }
            } catch (e) {
                console.log("Error extracting skill item:", e);
            }
        });
    }
    
    // Extract current company and title from first experience
    let currentCompany = null;
    let currentTitle = null;
    if (experiences.length > 0) {
        const first = experiences[0];
        if (first.duration && (first.duration.includes('Present') || first.duration.includes('present'))) {
            currentCompany = first.company;
            currentTitle = first.title;
        }
    }
    
    // Calculate total experience years (rough estimate)
    let totalExperienceYears = 0;
    experiences.forEach(exp => {
        if (exp.duration) {
            const yearMatch = exp.duration.match(/(\d+)\s*yr/i);
            if (yearMatch) {
                totalExperienceYears += parseInt(yearMatch[1]);
            }
        }
    });
    
    const result = {
        name,
        headline,
        location,
        about,
        experience: experiences,
        education,
        skills,
        linkedin_url: window.location.href,
        current_company: currentCompany,
        current_title: currentTitle,
        total_experience_years: totalExperienceYears > 0 ? totalExperienceYears : null,
        extraction_timestamp: new Date().toISOString(),
        data_completeness_score: 0.0  // Will be calculated later
    };
    
    console.log("Extraction complete:", result);
    return result;
})()
"""

# AI-powered profile analysis prompt using AdalFlow best practices
PROFILE_ANALYSIS_PROMPT = r"""<SYS>
You are an expert LinkedIn profile analyzer. Your task is to take raw extracted profile data and convert it into a clean, structured LinkedInProfile format.

Key responsibilities:
1. Parse and clean the raw data
2. Extract industry keywords from text
3. Calculate data completeness score
4. Structure all data according to the LinkedInProfile schema

Be thorough and accurate in your analysis.
</SYS>

Raw profile data to analyze:
{{ raw_data }}

Please analyze this raw LinkedIn profile data and return a structured response in the following JSON format:

{{ format_instructions }}

Focus on:
- Cleaning and normalizing text data
- Extracting relevant industry keywords from about/experience text
- Calculating accurate data completeness score (0-1)
- Ensuring all dates and durations are properly formatted
- Preserving all available information while structuring it properly

Return only valid JSON that matches the LinkedInProfile schema."""


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


# Create global extractor instance
_extractor = ProfileExtractor()


def extract_complete_profile(profile_url: str) -> dict:
    """Extract complete LinkedIn profile - function tool wrapper"""
    profile = _extractor.extract_complete_profile(profile_url)
    if profile:
        return profile.to_dict()
    else:
        return {"error": "Failed to extract profile", "url": profile_url}


def extract_current_profile() -> dict:
    """Extract profile from current page - function tool wrapper"""
    raw_data = _extractor.extract_raw_profile_data()
    if raw_data:
        profile = _extractor.parse_with_ai(raw_data)
        if not profile:
            profile = _extractor.fallback_parse(raw_data)
        return profile.to_dict()
    else:
        return {"error": "Failed to extract current profile"}


# Function tools for agent
ExtractCompleteProfileTool = FunctionTool(fn=extract_complete_profile)
ExtractCurrentProfileTool = FunctionTool(fn=extract_current_profile)