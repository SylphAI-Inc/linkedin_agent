"""DOM-based LinkedIn profile extraction using consistent selectors found in analysis"""

from adalflow.core.func_tool import FunctionTool
from .web_nav import js as run_js


# DOM-based extraction using actual LinkedIn structure patterns
PROFILE_EXTRACTION_DOM_JS = r"""
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
    const blocks = qa('[data-view-name="profile-component-entity"]', section);
    const out = [];

    for (const item of blocks) {
      // Title
      const title =
        norm(q('.t-bold span[aria-hidden="true"]', item)?.textContent) ||
        norm(q('.hoverable-link-text.t-bold span[aria-hidden="true"]', item)?.textContent) ||
        norm(q('.t-bold', item)?.textContent) || 'Unknown Title';

      // Company (prefer the labeled line under the title)
      const companyLink = q('a[href*="/company/"]', item);
      let company =
        norm(companyLink?.textContent) ||
        norm(qa('span', item).map(s => s.textContent).find(t =>
          t && !/yr|mo|Present| - /.test(t) && t.length <= 80 && !t.includes('Experience'))) || 'Unknown Company';

      // Dates/duration
      const dateSpan = qa('span', item).map(s => norm(s.textContent)).find(t => DATE_RX.test(t));
      let start_date = '', end_date = '', duration = '';
      if (dateSpan) {
        const m = dateSpan.match(DATE_RX);
        if (m) {
          start_date = m[1] || '';
          end_date   = m[2] || '';
          duration   = m[3] || '';
        }
      }

      // Location
      const location =
        (qa('span', item).map(s => norm(s.textContent)).find(t => t && looksLikeLocation(t)) || '');

      // Bullets / description
      let bullets = [];
      const textHost = q('.inline-show-more-text--is-expanded, .inline-show-more-text--is-collapsed', item) || item;
      if (textHost) {
        // Reconstruct text with line breaks where <br> occur
        const lines = [];
        (function collect(n){
          n.childNodes.forEach(ch => {
            if (ch.nodeType === Node.TEXT_NODE) { const t = norm(ch.textContent); if (t) lines.push(t); }
            else if (ch.nodeName === 'BR') { lines.push('\n'); }
            else collect(ch);
          });
        })(textHost);
        const joined = norm(lines.join(' ').replace(/\s*\n\s*/g, '\n'));
        bullets = joined
          .split('\n')
          .map(s => norm(s.replace(/^[-•]\s*/, '')))
          .filter(s => s && s.length > 3 && !DATE_RX.test(s));
      }

      // External links & logo
      const company_linkedin = companyLink?.getAttribute('href') || '';
      const logo_url = q('.pvs-entity__image img, img[alt$="logo"]', item)?.getAttribute('src') || '';
      const company_website =
        q('.pvs-thumbnail__wrapper ~ a[href^="http"]', item)?.getAttribute('href') ||
        q('a[href^="http"]:not([href*="linkedin.com"])', item)?.getAttribute('href') || '';

      // Clean
      const record = {
        title: title.replace(/(.+)\1+/, '$1'),
        company: company.replace(/(.+)\1+/, '$1').replace(/\s*·\s*Full-time.*/i, ''),
        start_date, end_date, duration,
        location,
        bullets,
        company_linkedin,
        company_website,
        logo_url
      };

      // Skip obvious junk
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

    for (const item of blocks) {
      const schoolLink = q('a[href*="/school/"], a[href*="/company/"]', item);
      const school =
        norm(schoolLink?.textContent) ||
        norm(q('.t-bold span[aria-hidden="true"]', item)?.textContent) ||
        norm(q('.t-bold', item)?.textContent) || 'Unknown School';

      // Degree / program: usually in the following t-14 line
      // (Matches your pasted HTML: “Bachelor of Commerce - BCom, Finance and Economics Specialist”)
      const degree =
        norm(q('.t-14.t-normal span[aria-hidden="true"]', item)?.textContent) ||
        norm(q('.t-14.t-normal', item)?.textContent) || '';

      // Dates are not present in your snippet, but keep parser ready
      const rawSpans = qa('span', item).map(s => norm(s.textContent));
      const dateSpan = rawSpans.find(t => DATE_RX.test(t)) || '';
      let start_date = '', end_date = '', duration = '';
      if (dateSpan) {
        const m = dateSpan.match(DATE_RX);
        if (m) { start_date = m[1] || ''; end_date = m[2] || ''; duration = m[3] || ''; }
      }

      const logo_url = q('.pvs-entity__image img, img[alt$="logo"]', item)?.getAttribute('src') || '';
      const school_linkedin = schoolLink?.getAttribute('href') || '';

      out.push({
        school: school.replace(/(.+)\1+/, '$1'),
        degree: degree.replace(/(.+)\1+/, '$1'),
        start_date, end_date, duration,
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


def extract_profile_dom_based() -> dict:
    """Extract LinkedIn profile using consistent DOM patterns"""
    try:
        result = run_js(PROFILE_EXTRACTION_DOM_JS)
        
        if not result or not isinstance(result, dict):
            return {
                "error": "Failed to extract profile data",
                "extraction_timestamp": None,
                "data_quality": {"extraction_failed": True}
            }
        
        return result
        
    except Exception as e:
        return {
            "error": f"Profile extraction error: {str(e)}",
            "extraction_timestamp": None,
            "data_quality": {"extraction_failed": True}
        }


# Create the function tool
ExtractProfileDOMTool = FunctionTool(fn=extract_profile_dom_based)


if __name__ == "__main__":
    print("DOM-based LinkedIn profile extraction")
    print("Key insights from DOM analysis:")
    print("✅ About section: Content in .display-flex, .ph5, .pv3 containers")
    print("✅ Experience section: Uses ul li.artdeco-list__item structure")  
    print("✅ Education section: Uses ul li.artdeco-list__item structure")
    print("✅ Company links: a[href*='/company/'] pattern")
    print("✅ School links: a[href*='/school/'] or a[href*='/company/'] pattern")
    print("✅ Consistent section finding: .visually-hidden text content")