from adalflow.core.func_tool import FunctionTool
from .web_nav import js as run_js
from typing import Dict, Any, List
import json
from datetime import datetime

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

# Enhanced validation and completeness functions
def validate_profile_data(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clean profile data"""
    if not profile_data:
        return {}
    
    # Ensure required fields exist with defaults
    validated = {
        "name": profile_data.get("name", "Unknown Name"),
        "headline": profile_data.get("headline", ""),
        "about": profile_data.get("about", ""),
        "experiences": profile_data.get("experiences", []),
        "education": profile_data.get("education", []),
        "skills": profile_data.get("skills", []),
        "certifications": profile_data.get("certifications", []),
        "languages": profile_data.get("languages", {}),
        "location": profile_data.get("location", ""),
        "url": profile_data.get("url", ""),
        "extraction_timestamp": profile_data.get("extraction_timestamp", datetime.now().isoformat()),
        "extraction_method": profile_data.get("extraction_method", "dom_based_enhanced")
    }
    
    # Clean and validate experiences
    clean_experiences = []
    for exp in validated["experiences"]:
        if isinstance(exp, dict) and exp.get("title") and exp.get("company"):
            clean_exp = {
                "title": str(exp.get("title", "")).strip(),
                "company": str(exp.get("company", "")).strip(),
                "duration": str(exp.get("duration", "")).strip(),
                "location": str(exp.get("location", "")).strip(),
                "description": str(exp.get("description", "")).strip()
            }
            # Skip if both title and company are "Unknown"
            if not (clean_exp["title"].lower().startswith("unknown") and 
                   clean_exp["company"].lower().startswith("unknown")):
                clean_experiences.append(clean_exp)
    
    validated["experiences"] = clean_experiences
    
    # Clean and validate education
    clean_education = []
    for edu in validated["education"]:
        if isinstance(edu, dict) and (edu.get("school") or edu.get("degree")):
            clean_edu = {
                "school": str(edu.get("school", "")).strip(),
                "degree": str(edu.get("degree", "")).strip(),
                "year": str(edu.get("year", "")).strip(),
                "field": str(edu.get("field", "")).strip()
            }
            clean_education.append(clean_edu)
    
    validated["education"] = clean_education
    
    # Clean skills - remove duplicates and noise
    if isinstance(validated["skills"], list):
        clean_skills = []
        seen = set()
        for skill in validated["skills"]:
            skill_str = str(skill)
            if skill_str:
                skill_str = skill_str.strip()
            if (skill_str and len(skill_str) > 2 and len(skill_str) < 50 and 
                skill_str.lower() not in seen and
                not any(noise in skill_str.lower() for noise in ['endorsed', 'endorse', 'months', 'show all'])):
                clean_skills.append(skill_str)
                seen.add(skill_str.lower())
        validated["skills"] = clean_skills[:15]  # Limit to top 15
    
    return validated

def calculate_enhanced_completeness(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate detailed completeness metrics"""
    if not profile_data:
        return {"total_score": 0, "completeness_percentage": 0}
    
    # Basic completeness (from original scoring)
    basic_score = profile_data.get("data_quality", {}).get("total_score", 0)
    
    # Enhanced completeness factors
    enhanced_factors = {
        "has_comprehensive_about": bool((profile_data.get("about") or "").strip() and len(profile_data.get("about") or "") > 100),
        "has_multiple_experiences": len(profile_data.get("experiences", [])) >= 2,
        "has_detailed_experiences": any(
            (exp.get("description") or "").strip() for exp in profile_data.get("experiences", [])
        ),
        "has_education_details": any(
            (edu.get("degree") or "").strip() for edu in profile_data.get("education", [])
        ),
        "has_certifications": len(profile_data.get("certifications", [])) > 0,
        "has_languages": bool(profile_data.get("languages", {}).get("items", [])),
        "has_diverse_skills": len(profile_data.get("skills", [])) >= 5,
        "has_recent_experience": any(
            "Present" in exp.get("duration", "") for exp in profile_data.get("experiences", [])
        )
    }
    
    enhanced_score = sum(enhanced_factors.values())
    total_possible = 6 + len(enhanced_factors)  # 6 basic + enhanced factors
    
    completeness_data = {
        "basic_score": basic_score,
        "enhanced_score": enhanced_score,
        "total_score": basic_score + enhanced_score,
        "max_possible": total_possible,
        "completeness_percentage": round((basic_score + enhanced_score) / total_possible * 100, 1),
        "factors": {
            "basic": {
                "has_name": bool((profile_data.get("name") or "").strip()),
                "has_headline": bool((profile_data.get("headline") or "").strip()),
                "has_about": bool((profile_data.get("about") or "").strip()),
                "has_experiences": len(profile_data.get("experiences", [])) > 0,
                "has_education": len(profile_data.get("education", [])) > 0,
                "has_location": bool((profile_data.get("location") or "").strip())
            },
            "enhanced": enhanced_factors
        }
    }
    
    return completeness_data

def extract_profile() -> Dict[str, Any]:
    """Enhanced DOM-based profile extraction with validation and completeness scoring"""
    try:
        # Run the proven DOM extraction JavaScript
        raw_data = run_js(PROFILE_JS)
        
        if not raw_data or not isinstance(raw_data, dict):
            return {
                "error": "Failed to extract profile data - no data returned",
                "extraction_timestamp": datetime.now().isoformat(),
                "extraction_method": "dom_based_enhanced",
                "extraction_success": False
            }
        
        # Validate and clean the data
        validated_data = validate_profile_data(raw_data)
        
        # Calculate enhanced completeness (with extra safety)
        try:
            completeness = calculate_enhanced_completeness(validated_data)
        except Exception as completeness_error:
            # Fallback to basic scoring if enhanced completeness fails
            completeness = {
                "total_score": 0,
                "completeness_percentage": 0,
                "error": f"Completeness calculation failed: {str(completeness_error)}"
            }
        
        # Add completeness to the result
        validated_data["data_quality"] = completeness
        validated_data["extraction_success"] = True
        
        return validated_data
        
    except Exception as e:
        return {
            "error": f"Profile extraction failed: {str(e)}",
            "extraction_timestamp": datetime.now().isoformat(),
            "extraction_method": "dom_based_enhanced",
            "extraction_success": False
        }

# Enhanced extraction functions for different use cases
def extract_complete_profile(profile_url: str = None) -> Dict[str, Any]:
    """Extract complete profile - handles URL navigation if provided"""
    if profile_url:
        from .web_nav import go
        go(profile_url)
    
    return extract_profile()

# Function tools for agent
ExtractCompleteProfileTool = FunctionTool(fn=extract_complete_profile)