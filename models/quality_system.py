#!/usr/bin/env python3
"""
Phase 1: Quality-Driven Adaptive Search System

Core components:
- Quality thresholds and scoring
- Adaptive search budget
- Intelligent search extension
- Heap-based candidate ranking
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import heapq
import statistics


@dataclass
class QualityThresholds:
    """Define quality scoring thresholds for different candidate tiers"""
    minimum_acceptable: float = 4.0      # Baseline - worth considering
    target_quality: float = 7.0          # Good candidates we're aiming for
    exceptional_quality: float = 9.0     # Outstanding - auto-include these
    
    # Quality plateau detection
    plateau_window: int = 10             # Look at last N candidates
    plateau_improvement_threshold: float = 0.5  # Must improve by this much


@dataclass  
class SearchBudget:
    """Define search effort constraints and extension logic"""
    initial_page_limit: int = 3          # Start with this many pages
    max_page_limit: int = 8              # Never go beyond this
    max_time_minutes: int = 20           # Total time budget
    max_candidates_evaluated: int = 100  # Evaluation budget
    
    # Extension triggers
    low_quality_threshold: float = 4.0   # Extend if average quality below this
    min_acceptable_candidates: int = 3   # Need at least this many good ones
    

@dataclass
class CandidateQuality:
    """Comprehensive candidate quality assessment"""
    overall_score: float
    technical_score: float
    experience_score: float  
    cultural_fit_score: float
    
    # Quality explanation
    strengths: List[str]
    concerns: List[str]
    key_signals: Dict[str, Any]
    
    # Metadata
    extraction_quality: float  # How good was the data extraction?
    profile_completeness: float
    timestamp: str


class CandidateHeap:
    """Heap-based priority queue for maintaining top N candidates"""
    
    def __init__(self, max_size: int = 20, min_score_threshold: float = 0.0):
        self.max_size = max_size
        self.min_score_threshold = min_score_threshold
        self.heap = []  # Min-heap (lowest scores first)
        self.seen_urls = set()  # Deduplication
        
    def add_candidate(self, candidate_data: Dict[str, Any], quality: CandidateQuality):
        """Add candidate if quality is good enough, maintaining heap size"""
        url = candidate_data.get('url', '')
        
        # Skip duplicates
        if url in self.seen_urls:
            return False, "duplicate"
        
        # Check absolute minimum threshold first
        if quality.overall_score < self.min_score_threshold:
            return False, "below_minimum_threshold"
            
        # Always add if heap not full
        if len(self.heap) < self.max_size:
            heapq.heappush(self.heap, (quality.overall_score, url, candidate_data, quality))
            self.seen_urls.add(url)
            return True, "added_to_heap"
        
        # If heap full, only add if better than worst candidate
        worst_score = self.heap[0][0]
        if quality.overall_score > worst_score:
            # Remove worst, add new
            old_item = heapq.heappop(self.heap)
            self.seen_urls.discard(old_item[1])  # Remove old URL from seen set
            
            heapq.heappush(self.heap, (quality.overall_score, url, candidate_data, quality))
            self.seen_urls.add(url)
            return True, "replaced_worse_candidate"
        
        return False, "quality_too_low"
    
    def get_top_candidates(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get top candidates sorted by quality (best first)"""
        if not self.heap:
            return []
            
        # Sort heap by score descending (best first)
        sorted_candidates = sorted(self.heap, key=lambda x: x[0], reverse=True)
        
        if limit:
            sorted_candidates = sorted_candidates[:limit]
            
        return [
            {
                **candidate_data,
                "quality_assessment": quality,
                "heap_rank": i + 1
            }
            for i, (score, url, candidate_data, quality) in enumerate(sorted_candidates)
        ]
    
    def get_quality_stats(self) -> Dict[str, float]:
        """Get quality statistics for decision making"""
        if not self.heap:
            return {"count": 0, "average": 0, "min": 0, "max": 0, "median": 0}
            
        scores = [item[0] for item in self.heap]
        return {
            "count": len(scores),
            "average": statistics.mean(scores),
            "min": min(scores),
            "max": max(scores),
            "median": statistics.median(scores)
        }
    
    def needs_more_candidates(self, thresholds: QualityThresholds) -> bool:
        """Determine if we need to continue searching"""
        if len(self.heap) == 0:
            return True
            
        stats = self.get_quality_stats()
        
        # Need more if average quality is low
        if stats["average"] < thresholds.target_quality:
            return True
            
        # Need more if we don't have enough acceptable candidates
        acceptable_count = sum(1 for score, _, _, _ in self.heap 
                             if score >= thresholds.minimum_acceptable)
        
        return acceptable_count < 3  # Need at least 3 acceptable candidates
    
    def is_ready_for_extraction(self, min_avg_threshold: float = 5.0, min_candidates: int = 3) -> tuple:
        """Determine if heap quality is good enough to proceed with profile extraction"""
        if len(self.heap) < min_candidates:
            return False, f"insufficient_candidates_{len(self.heap)}"
            
        stats = self.get_quality_stats()
        avg_quality = stats.get('average', 0)
        
        if avg_quality < min_avg_threshold:
            return False, f"low_average_quality_{avg_quality:.1f}"
            
        return True, f"quality_ready_avg_{avg_quality:.1f}"


class QualityAnalyzer:
    """Analyze candidate quality and make search decisions"""
    
    def __init__(self, thresholds: QualityThresholds, budget: SearchBudget):
        self.thresholds = thresholds
        self.budget = budget
        self.quality_history = []  # Track quality over time
        
    def assess_candidate_quality(self, candidate_data: Dict[str, Any], 
                                headline_score: float) -> CandidateQuality:
        """Comprehensive quality assessment of a candidate"""
        
        # Extract key data
        name = candidate_data.get('name', '')
        headline = candidate_data.get('headline', '')
        profile_data = candidate_data.get('profile_data', {})
        
        # Calculate component scores
        technical_score = self._assess_technical_quality(headline, profile_data, headline_score)
        experience_score = self._assess_experience_quality(profile_data)
        cultural_fit_score = self._assess_cultural_fit(headline, profile_data)
        extraction_quality = self._assess_extraction_quality(candidate_data)
        
        # Overall score (weighted average)
        overall_score = (
            technical_score * 0.35 +
            experience_score * 0.35 + 
            cultural_fit_score * 0.20 +
            extraction_quality * 0.10
        )
        
        # Generate explanations
        strengths, concerns = self._generate_quality_explanations(
            technical_score, experience_score, cultural_fit_score, headline, profile_data
        )
        
        return CandidateQuality(
            overall_score=round(overall_score, 2),
            technical_score=round(technical_score, 2),
            experience_score=round(experience_score, 2),
            cultural_fit_score=round(cultural_fit_score, 2),
            strengths=strengths,
            concerns=concerns,
            key_signals={
                "headline_score": headline_score,
                "has_profile_data": bool(profile_data),
                "profile_completeness": len(profile_data.keys()) if profile_data else 0
            },
            extraction_quality=round(extraction_quality, 2),
            profile_completeness=self._calculate_profile_completeness(profile_data),
            timestamp=datetime.now().isoformat()
        )
    
    def _assess_technical_quality(self, headline: str, profile_data: Dict[str, Any], 
                                 headline_score: float) -> float:
        """Assess technical competency indicators"""
        score = headline_score  # Base score from headline analysis
        
        if profile_data:
            # Boost for detailed experience
            experiences = profile_data.get('experiences', [])
            if len(experiences) >= 3:
                score += 1.0
                
            # Boost for education
            education = profile_data.get('education', [])
            if education:
                score += 0.5
                
            # Boost for skills
            skills = profile_data.get('skills', [])
            if len(skills) >= 10:
                score += 1.0
                
        return min(score, 10.0)  # Cap at 10
    
    def _assess_experience_quality(self, profile_data: Dict[str, Any]) -> float:
        """Assess experience depth and progression"""
        if not profile_data:
            return 3.0  # Neutral score for missing data
            
        score = 5.0  # Base score
        
        experiences = profile_data.get('experiences', [])
        
        # Experience quantity
        if len(experiences) >= 3:
            score += 1.5
        elif len(experiences) >= 2:
            score += 1.0
            
        # Look for progression indicators
        for exp in experiences[:3]:  # Check recent experience
            title = exp.get('title', '').lower()
            if any(word in title for word in ['senior', 'lead', 'staff', 'principal', 'architect']):
                score += 1.0
                break
                
        return min(score, 10.0)
    
    def _assess_cultural_fit(self, headline: str, profile_data: Dict[str, Any]) -> float:
        """Assess cultural fit indicators"""
        score = 5.0  # Neutral base
        
        # Communication quality (from profile completeness)
        if profile_data and profile_data.get('about'):
            score += 1.0
            
        # Collaborative indicators
        headline_lower = headline.lower()
        if any(word in headline_lower for word in ['team', 'collaboration', 'agile', 'scrum']):
            score += 0.5
            
        return min(score, 10.0)
    
    def _assess_extraction_quality(self, candidate_data: Dict[str, Any]) -> float:
        """How good was our data extraction?"""
        score = 0.0
        
        # Basic fields present
        if candidate_data.get('name'):
            score += 2.0
        if candidate_data.get('headline'):  
            score += 2.0
        if candidate_data.get('url'):
            score += 1.0
        if candidate_data.get('profile_data'):
            score += 5.0
            
        return min(score, 10.0)
    
    def _calculate_profile_completeness(self, profile_data: Dict[str, Any]) -> float:
        """Calculate how complete the profile data is"""
        if not profile_data:
            return 0.0
            
        fields = ['experiences', 'education', 'skills', 'about']
        present_fields = sum(1 for field in fields if profile_data.get(field))
        
        return (present_fields / len(fields)) * 100
    
    def _generate_quality_explanations(self, tech_score: float, exp_score: float, 
                                     cultural_score: float, headline: str, 
                                     profile_data: Dict[str, Any]) -> tuple:
        """Generate human-readable quality explanations"""
        strengths = []
        concerns = []
        
        # Technical strengths/concerns
        if tech_score >= 7:
            strengths.append("Strong technical background")
        elif tech_score < 4:
            concerns.append("Limited technical indicators")
            
        # Experience strengths/concerns  
        if exp_score >= 7:
            strengths.append("Solid experience progression")
        elif exp_score < 4:
            concerns.append("Limited experience information")
            
        # Profile completeness
        if profile_data:
            experiences = len(profile_data.get('experiences', []))
            if experiences >= 3:
                strengths.append(f"{experiences} work experiences listed")
            elif experiences == 0:
                concerns.append("No work experience details")
        else:
            concerns.append("Profile extraction incomplete")
            
        return strengths, concerns
    
    def assess_candidate_quality_integrated(self, candidate_data: Dict[str, Any], 
                                          strategy: Dict[str, Any],
                                          min_score_threshold: float) -> CandidateQuality:
        """Integrated quality assessment: headline scoring + comprehensive quality in one step"""
        
        # Extract key data
        name = candidate_data.get('name', '')
        headline = candidate_data.get('headline', '')
        url = candidate_data.get('url', '')
        
        # Step 1: Do headline scoring using strategy (replaces old evaluate_headline_with_strategy)
        headline_score = self._evaluate_headline_with_strategy(headline, strategy)
        
        # Step 2: Do comprehensive quality assessment
        technical_score = self._assess_technical_quality_integrated(headline, headline_score, strategy)
        experience_score = self._assess_experience_quality_integrated(headline, strategy)
        cultural_fit_score = self._assess_cultural_fit(headline, {})  # No profile data yet
        extraction_quality = 8.0 if all([name, headline, url]) else 4.0  # Basic data completeness
        
        # Step 3: Apply scoring boosts
        company_score_boost = self._assess_company_quality_boost(headline, strategy)
        seniority_score_boost = self._assess_seniority_quality_boost(headline, strategy)
        
        # Overall score (weighted average + boosts)
        base_score = (
            technical_score * 0.35 +
            experience_score * 0.35 + 
            cultural_fit_score * 0.20 +
            extraction_quality * 0.10
        )
        overall_score = base_score + company_score_boost + seniority_score_boost
        
        # Generate explanations (including boost info)
        strengths, concerns = self._generate_quality_explanations_integrated(
            technical_score, experience_score, cultural_fit_score, headline, strategy, 
            company_score_boost, seniority_score_boost
        )
        
        return CandidateQuality(
            overall_score=round(overall_score, 2),
            technical_score=round(technical_score, 2),
            experience_score=round(experience_score, 2),
            cultural_fit_score=round(cultural_fit_score, 2),
            strengths=strengths,
            concerns=concerns,
            key_signals={
                "headline_score": headline_score,
                "company_boost": company_score_boost,
                "seniority_boost": seniority_score_boost,
                "base_score": round(base_score, 2),
                "total_boost": round(company_score_boost + seniority_score_boost, 2),
                "strategy_format": "agent" if "primary_titles" in strategy else "fallback",
                "headline_length": len(headline) if headline else 0
            },
            extraction_quality=round(extraction_quality, 2),
            profile_completeness=0.0,  # No full profile data yet
            timestamp=datetime.now().isoformat()
        )
    
    def _evaluate_headline_with_strategy(self, headline: str, strategy: Dict[str, Any]) -> float:
        """Evaluate headline using strategy - integrated version"""
        if not headline or not strategy:
            return 0.0
            
        headline_lower = headline.lower()
        score = 0.0
        
        # Handle both strategy formats: agent format and expected format
        if "headline_analysis" in strategy:
            # Expected format from fallback strategy
            target_titles = [title.lower() for title in strategy.get("headline_analysis", {}).get("target_job_titles", [])]
            alternative_titles = [title.lower() for title in strategy.get("headline_analysis", {}).get("alternative_titles", [])]
            seniority_keywords = [kw.lower() for kw in strategy.get("headline_analysis", {}).get("seniority_keywords", [])]
            company_indicators = [comp.lower() for comp in strategy.get("headline_analysis", {}).get("company_indicators", [])]
            tech_signals = [tech.lower() for tech in strategy.get("headline_analysis", {}).get("tech_stack_signals", [])]
            negative_patterns = [pattern.lower() for pattern in strategy.get("search_filtering", {}).get("negative_headline_patterns", [])]
        else:
            # Agent format - convert to expected format
            target_titles = [title.lower() for title in strategy.get("primary_titles", [])]
            alternative_titles = [title.lower() for title in strategy.get("alternative_titles", [])]
            seniority_keywords = [kw.lower() for kw in strategy.get("seniority_indicators", [])]
            company_indicators = [comp.lower() for comp in strategy.get("target_companies", [])]
            tech_signals = [tech.lower() for tech in strategy.get("key_technologies", [])]
            negative_patterns = [pattern.lower() for pattern in strategy.get("negative_patterns", [])]
        
        # Job title relevance
        if any(title in headline_lower for title in target_titles):
            score += 3.0
        elif any(alt in headline_lower for alt in alternative_titles):
            score += 2.0
        
        # Seniority indicators
        if any(keyword in headline_lower for keyword in seniority_keywords):
            score += 1.5
        
        # Company indicators
        if any(indicator in headline_lower for indicator in company_indicators):
            score += 1.0
        
        # Tech stack signals
        matching_tech = [tech for tech in tech_signals if tech in headline_lower]
        if matching_tech:
            score += len(matching_tech) * 0.5
        
        # Check for negative patterns
        if any(pattern in headline_lower for pattern in negative_patterns):
            score -= 2.0
            
        return max(score, 0.0)  # Don't go negative
    
    def _assess_technical_quality_integrated(self, headline: str, headline_score: float, 
                                           strategy: Dict[str, Any]) -> float:
        """Assess technical quality using headline and strategy"""
        score = headline_score  # Base score from headline analysis
        
        # Boost for technical depth indicators in headline
        headline_lower = headline.lower() if headline else ""
        
        # Look for architecture/design keywords
        if any(word in headline_lower for word in ['architect', 'design', 'lead', 'principal']):
            score += 1.0
            
        # Look for specific tech mentions beyond basic keywords
        tech_depth_indicators = ['full stack', 'backend', 'frontend', 'devops', 'ml', 'ai']
        if any(indicator in headline_lower for indicator in tech_depth_indicators):
            score += 0.5
            
        return min(score, 10.0)
    
    def _assess_experience_quality_integrated(self, headline: str, strategy: Dict[str, Any]) -> float:
        """Assess experience quality from headline indicators"""
        score = 5.0  # Base score
        headline_lower = headline.lower() if headline else ""
        
        # Seniority indicators
        seniority_words = ['senior', 'lead', 'staff', 'principal', 'director']
        if any(word in headline_lower for word in seniority_words):
            score += 2.0
        elif any(word in headline_lower for word in ['jr', 'junior', 'entry']):
            score -= 1.0
            
        # Company quality indicators (if we recognize the company)
        company_indicators = strategy.get("target_companies", []) if "target_companies" in strategy else strategy.get("headline_analysis", {}).get("company_indicators", [])
        if any(comp.lower() in headline_lower for comp in company_indicators):
            score += 1.0
            
        return min(score, 10.0)
    
    def _generate_quality_explanations_integrated(self, tech_score: float, exp_score: float, 
                                                cultural_score: float, headline: str, 
                                                strategy: Dict[str, Any], company_boost: float = 0.0, 
                                                seniority_boost: float = 0.0) -> tuple:
        """Generate human-readable quality explanations for integrated assessment"""
        strengths = []
        concerns = []
        
        # Technical strengths/concerns
        if tech_score >= 7:
            strengths.append("Strong technical indicators in headline")
        elif tech_score < 4:
            concerns.append("Limited technical keywords found")
            
        # Experience strengths/concerns  
        if exp_score >= 7:
            strengths.append("Strong seniority/experience indicators")
        elif exp_score < 4:
            concerns.append("Limited experience indicators")
            
        # Headline quality
        if headline and len(headline) > 30:
            strengths.append("Detailed professional headline")
        elif not headline or len(headline) < 10:
            concerns.append("Very brief or missing headline")
        
        # Company boost information
        if company_boost > 0:
            if company_boost >= 1.5:
                strengths.append(f"Works at target tier-1 company (+{company_boost:.1f} boost)")
            elif company_boost >= 1.0:
                strengths.append(f"Works at target tier-2 company (+{company_boost:.1f} boost)")
            else:
                strengths.append(f"Works at target company (+{company_boost:.1f} boost)")
        
        # Seniority boost information
        if seniority_boost > 0:
            if seniority_boost >= 1.5:
                strengths.append(f"Senior/leadership role (+{seniority_boost:.1f} boost)")
            elif seniority_boost >= 1.0:
                strengths.append(f"Mid-senior level role (+{seniority_boost:.1f} boost)")
            else:
                strengths.append(f"Seniority indicators (+{seniority_boost:.1f} boost)")
            
        return strengths, concerns
    
    def _assess_company_quality_boost(self, headline: str, strategy: Dict[str, Any]) -> float:
        """Assess company-based quality boost from headline"""
        if not headline or not strategy:
            return 0.0
            
        headline_lower = headline.lower()
        boost = 0.0
        
        # Extract target companies from strategy
        target_companies = []
        if "target_companies" in strategy:
            target_companies = strategy["target_companies"]
        elif "headline_analysis" in strategy and "company_indicators" in strategy["headline_analysis"]:
            target_companies = strategy["headline_analysis"]["company_indicators"]
        
        if not target_companies:
            return 0.0
            
        # Define company tiers with different boost values
        tier_1_companies = ["google", "facebook", "meta", "apple", "microsoft", "amazon", "netflix", "tesla", "uber", "airbnb"]
        tier_2_companies = ["stripe", "dropbox", "slack", "salesforce", "adobe", "nvidia", "twitter", "linkedin", "pinterest", "square"]
        
        # Check for exact company mentions in headline
        for company in target_companies:
            company_lower = company.lower()
            
            # Look for company name in headline (with word boundaries)
            import re
            if re.search(r'\b' + re.escape(company_lower) + r'\b', headline_lower):
                # Tier-based scoring
                if company_lower in tier_1_companies:
                    boost += 1.5  # Big boost for top tier companies
                elif company_lower in tier_2_companies:
                    boost += 1.0  # Medium boost for tier 2 companies
                else:
                    boost += 0.75  # Standard boost for target companies
                    
                # Additional boost if they explicitly mention working "at" the company
                if f" at {company_lower}" in headline_lower or f"@{company_lower}" in headline_lower:
                    boost += 0.25
                    
                break  # Only apply boost for first matching company
        
        return min(boost, 2.0)  # Cap boost at 2.0 points
    
    def _assess_seniority_quality_boost(self, headline: str, strategy: Dict[str, Any]) -> float:
        """Assess seniority-based quality boost from headline using strategy data"""
        if not headline or not strategy:
            return 0.0
            
        headline_lower = headline.lower()
        boost = 0.0
        
        # Extract seniority indicators from strategy
        seniority_indicators = []
        if "seniority_indicators" in strategy:
            seniority_indicators = [s.lower() for s in strategy["seniority_indicators"]]
        elif "headline_analysis" in strategy and "seniority_keywords" in strategy["headline_analysis"]:
            seniority_indicators = [s.lower() for s in strategy["headline_analysis"]["seniority_keywords"]]
        
        # Extract primary and alternative titles from strategy  
        primary_titles = []
        alternative_titles = []
        if "primary_titles" in strategy:
            primary_titles = [t.lower() for t in strategy["primary_titles"]]
        elif "headline_analysis" in strategy and "target_job_titles" in strategy["headline_analysis"]:
            primary_titles = [t.lower() for t in strategy["headline_analysis"]["target_job_titles"]]
            
        if "alternative_titles" in strategy:
            alternative_titles = [t.lower() for t in strategy["alternative_titles"]]
        elif "headline_analysis" in strategy and "alternative_titles" in strategy["headline_analysis"]:
            alternative_titles = [t.lower() for t in strategy["headline_analysis"]["alternative_titles"]]
        
        # Categorize seniority levels based on common patterns
        executive_words = ["cto", "ceo", "vp", "vice president", "director", "head of", "chief"]
        principal_words = ["principal", "staff", "architect", "distinguished"] 
        senior_words = ["senior", "lead", "sr.", "sr ", "team lead", "tech lead", "technical lead"]
        
        # Check for seniority match in strategy indicators
        matched_seniority = [s for s in seniority_indicators if s in headline_lower]
        
        if matched_seniority:
            # Determine boost level based on matched seniority terms
            for term in matched_seniority:
                if any(exec_word in term for exec_word in executive_words):
                    boost = max(boost, 2.0)  # Executive level
                elif any(prin_word in term for prin_word in principal_words):
                    boost = max(boost, 1.8)  # Principal/Staff level
                elif any(sr_word in term for sr_word in senior_words):
                    boost = max(boost, 1.5)  # Senior level
                else:
                    boost = max(boost, 1.0)  # General seniority indicator
        
        # Check for title relevance boost
        title_relevance_boost = 0.0
        if any(title in headline_lower for title in primary_titles):
            title_relevance_boost = 0.5  # Boost for exact primary title match
        elif any(title in headline_lower for title in alternative_titles):
            title_relevance_boost = 0.3  # Smaller boost for alternative title
            
        # Extract key technologies from strategy for additional context
        key_technologies = []
        if "key_technologies" in strategy:
            key_technologies = [t.lower() for t in strategy["key_technologies"]]
        elif "headline_analysis" in strategy and "tech_stack_signals" in strategy["headline_analysis"]:
            key_technologies = [t.lower() for t in strategy["headline_analysis"]["tech_stack_signals"]]
        
        # Additional context boosts based on strategy
        context_boost = 0.0
        if boost > 0 and key_technologies:
            # Boost for mentioning strategy-relevant technologies
            tech_matches = [tech for tech in key_technologies if tech in headline_lower]
            if tech_matches:
                context_boost = min(len(tech_matches) * 0.1, 0.3)  # Max 0.3 boost
        
        total_boost = boost + title_relevance_boost + context_boost
        return min(total_boost, 2.0)  # Cap total boost at 2.0 points
    
    def should_extend_search(self, current_stats: Dict[str, float], 
                           pages_searched: int) -> tuple:
        """Decide whether to extend search based on quality"""
        
        # Don't extend if we've hit hard limits
        if pages_searched >= self.budget.max_page_limit:
            return False, "hit_page_limit"
            
        # Extend if overall quality is low
        if current_stats["average"] < self.budget.low_quality_threshold:
            return True, f"low_average_quality_{current_stats['average']:.1f}"
            
        # Extend if we don't have enough acceptable candidates
        if current_stats["count"] < self.budget.min_acceptable_candidates:
            return True, f"insufficient_candidates_{current_stats['count']}"
            
        return False, "quality_sufficient"
    
    def detect_quality_plateau(self, recent_scores: List[float]) -> bool:
        """Detect if quality has plateaued (no improvement)"""
        if len(recent_scores) < self.thresholds.plateau_window:
            return False
            
        recent_window = recent_scores[-self.thresholds.plateau_window:]
        first_half = recent_window[:len(recent_window)//2]
        second_half = recent_window[len(recent_window)//2:]
        
        if not first_half or not second_half:
            return False
            
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        improvement = second_avg - first_avg
        return improvement < self.thresholds.plateau_improvement_threshold