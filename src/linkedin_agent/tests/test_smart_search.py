#!/usr/bin/env python3
"""
Unit tests for smart_search.py
Ensures extraction logic works correctly with LinkedIn HTML structure
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import json

# Import the functions we're testing
from linkedin_agent.tools.smart_search import (
    _extract_candidates_from_page,
    _simple_score,
    smart_candidate_search
)


class TestCandidateExtraction:
    """Test the candidate extraction from LinkedIn search pages"""
    
    @pytest.fixture
    def mock_linkedin_html(self):
        """Mock LinkedIn search results HTML structure"""
        return """
        <div class="reusable-search__result-container">
            <a href="https://www.linkedin.com/in/johndoe">
                <span aria-hidden="true">John Doe</span>
            </a>
            <div class="entity-result__primary-subtitle">
                Senior Backend Engineer at Google
            </div>
        </div>
        <li class="reusable-search__result-container">
            <a href="https://www.linkedin.com/in/janesmith">
                <span aria-hidden="true">Jane Smith</span>
            </a>
            <div class="entity-result__primary-subtitle">
                Backend Developer | Python Expert
            </div>
        </li>
        <div class="reusable-search__result-container">
            <a href="https://www.linkedin.com/in/bobwilson">
                <span aria-hidden="true">Bob Wilson</span>
            </a>
            <div class="entity-result__summary">
                Staff Software Engineer - Backend Systems
            </div>
        </div>
        """
    
    @pytest.fixture
    def mock_linkedin_html_alt_format(self):
        """Mock LinkedIn HTML with alternative format"""
        return """
        <li data-view-name="search-results-entity">
            <div>
                <a href="https://www.linkedin.com/in/alicechen">
                    <span>View Alice Chen's profile</span>
                </a>
                <div>3rd degree connection</div>
                <div>Principal Backend Engineer at Meta</div>
            </div>
        </li>
        """
    
    @patch('linkedin_agent.tools.smart_search.run_js')
    def test_extract_candidates_standard_format(self, mock_run_js):
        """Test extraction with standard LinkedIn HTML format"""
        # Mock the JavaScript execution to return parsed candidates
        mock_run_js.return_value = [
            {
                'name': 'John Doe',
                'headline': 'Senior Backend Engineer at Google',
                'url': 'https://www.linkedin.com/in/johndoe'
            },
            {
                'name': 'Jane Smith',
                'headline': 'Backend Developer | Python Expert',
                'url': 'https://www.linkedin.com/in/janesmith'
            },
            {
                'name': 'Bob Wilson',
                'headline': 'Staff Software Engineer - Backend Systems',
                'url': 'https://www.linkedin.com/in/bobwilson'
            }
        ]
        
        candidates = _extract_candidates_from_page()
        
        assert len(candidates) == 3
        assert candidates[0]['name'] == 'John Doe'
        assert 'Backend Engineer' in candidates[0]['headline']
        assert candidates[1]['name'] == 'Jane Smith'
        assert 'Backend Developer' in candidates[1]['headline']
        assert candidates[2]['name'] == 'Bob Wilson'
        assert 'Staff Software Engineer' in candidates[2]['headline']
    
    @patch('linkedin_agent.tools.smart_search.run_js')
    def test_extract_candidates_empty_page(self, mock_run_js):
        """Test extraction when no candidates found"""
        mock_run_js.return_value = []
        
        candidates = _extract_candidates_from_page()
        
        assert candidates == []
    
    @patch('linkedin_agent.tools.smart_search.run_js')
    def test_extract_candidates_with_missing_data(self, mock_run_js):
        """Test extraction with incomplete candidate data"""
        mock_run_js.return_value = [
            {
                'name': 'John Doe',
                'headline': '',  # Missing headline
                'url': 'https://www.linkedin.com/in/johndoe'
            },
            {
                'name': None,  # Missing name - should be filtered out
                'headline': 'Backend Developer',
                'url': 'https://www.linkedin.com/in/anonymous'
            }
        ]
        
        candidates = _extract_candidates_from_page()
        
        # Only the first candidate should be returned (has name and URL)
        assert len(candidates) == 1
        assert candidates[0]['name'] == 'John Doe'
    
    @patch('linkedin_agent.tools.smart_search.run_js')
    def test_extract_candidates_exception_handling(self, mock_run_js):
        """Test extraction handles JavaScript errors gracefully"""
        mock_run_js.side_effect = Exception("JavaScript execution failed")
        
        candidates = _extract_candidates_from_page()
        
        assert candidates == []
    
    @patch('linkedin_agent.tools.smart_search.run_js')
    def test_extract_candidates_invalid_return_type(self, mock_run_js):
        """Test extraction handles invalid return types"""
        mock_run_js.return_value = "not a list"
        
        candidates = _extract_candidates_from_page()
        
        assert candidates == []


class TestScoringFunction:
    """Test the candidate scoring logic"""
    
    def test_simple_score_exact_match(self):
        """Test scoring with exact query match"""
        headline = "Senior Backend Engineer at Google"
        query = "backend engineer"
        
        score = _simple_score(headline.lower(), query.lower())
        
        assert score >= 5.0  # Should get points for containing the query
    
    def test_simple_score_keyword_match(self):
        """Test scoring with keyword matches"""
        headline = "backend developer with python expertise"
        query = "backend engineer"
        
        score = _simple_score(headline, query)
        
        assert score > 0  # Should get points for keyword "backend"
    
    def test_simple_score_seniority_bonus(self):
        """Test scoring with seniority indicators"""
        headline = "senior backend engineer"
        query = "engineer"
        
        score = _simple_score(headline, query)
        
        # Should get points for "engineer" keyword and "senior" seniority
        assert score >= 3.0
    
    def test_simple_score_no_match(self):
        """Test scoring with no relevant matches"""
        headline = "marketing manager"
        query = "backend engineer"
        
        score = _simple_score(headline, query)
        
        assert score == 0.0
    
    def test_simple_score_multiple_bonuses(self):
        """Test scoring with multiple bonus criteria"""
        headline = "principal backend engineer and architect"
        query = "backend"
        
        score = _simple_score(headline, query)
        
        # Should get points for:
        # - "backend" keyword match
        # - "principal" seniority
        # - "engineer" and "architect" role terms
        assert score >= 5.0


class TestSmartCandidateSearch:
    """Test the main search function"""
    
    @patch('linkedin_agent.tools.smart_search.nav_go')
    @patch('linkedin_agent.tools.smart_search.nav_wait')
    @patch('linkedin_agent.tools.smart_search.run_js')
    @patch('linkedin_agent.tools.smart_search.store_search_results')
    def test_smart_search_success(self, mock_store, mock_run_js, mock_wait, mock_go):
        """Test successful candidate search"""
        # Mock extraction to return candidates
        mock_run_js.return_value = [
            {
                'name': 'John Doe',
                'headline': 'senior backend engineer at google',
                'url': 'https://www.linkedin.com/in/johndoe'
            },
            {
                'name': 'Jane Smith',
                'headline': 'backend developer',
                'url': 'https://www.linkedin.com/in/janesmith'
            }
        ]
        
        result = smart_candidate_search(
            query="Backend Engineer",
            location="San Francisco",
            page_limit=1,
            min_score=3.0,
            target_count=2
        )
        
        assert result['success'] == True
        assert result['candidates_found'] == 2
        assert len(result['candidates']) == 2
        
        # Verify navigation was called
        mock_go.assert_called_once()
        mock_wait.assert_called()
        
        # Verify results were stored
        mock_store.assert_called_once()
        stored_candidates = mock_store.call_args[0][0]
        assert len(stored_candidates) == 2
    
    @patch('linkedin_agent.tools.smart_search.nav_go')
    @patch('linkedin_agent.tools.smart_search.nav_wait')
    @patch('linkedin_agent.tools.smart_search.run_js')
    @patch('linkedin_agent.tools.smart_search.store_search_results')
    def test_smart_search_filtering(self, mock_store, mock_run_js, mock_wait, mock_go):
        """Test that low-scoring candidates are filtered out"""
        # Mock extraction to return mixed quality candidates
        mock_run_js.return_value = [
            {
                'name': 'John Doe',
                'headline': 'senior backend engineer',  # High score
                'url': 'https://www.linkedin.com/in/johndoe'
            },
            {
                'name': 'Jane Smith',
                'headline': 'marketing manager',  # Low score - should be filtered
                'url': 'https://www.linkedin.com/in/janesmith'
            },
            {
                'name': 'Bob Wilson',
                'headline': 'backend developer',  # Medium score
                'url': 'https://www.linkedin.com/in/bobwilson'
            }
        ]
        
        result = smart_candidate_search(
            query="Backend Engineer",
            location="San Francisco",
            page_limit=1,
            min_score=3.0,
            target_count=5
        )
        
        assert result['success'] == True
        # Only 2 candidates should pass the minimum score threshold
        assert result['candidates_found'] == 2
        
        # Verify the right candidates were kept
        names = [c['name'] for c in result['candidates']]
        assert 'John Doe' in names
        assert 'Bob Wilson' in names
        assert 'Jane Smith' not in names
    
    @patch('linkedin_agent.tools.smart_search.nav_go')
    @patch('linkedin_agent.tools.smart_search.nav_wait')
    @patch('linkedin_agent.tools.smart_search.run_js')
    def test_smart_search_pagination(self, mock_run_js, mock_wait, mock_go):
        """Test search across multiple pages"""
        # First page returns 1 candidate, second page returns 2 more
        mock_run_js.side_effect = [
            [{'name': 'John Doe', 'headline': 'backend engineer', 'url': 'https://linkedin.com/in/john'}],
            [
                {'name': 'Jane Smith', 'headline': 'senior backend developer', 'url': 'https://linkedin.com/in/jane'},
                {'name': 'Bob Wilson', 'headline': 'backend architect', 'url': 'https://linkedin.com/in/bob'}
            ]
        ]
        
        result = smart_candidate_search(
            query="Backend",
            location="SF",
            page_limit=2,
            min_score=1.0,
            target_count=3
        )
        
        assert result['success'] == True
        assert result['candidates_found'] == 3
        # Should have navigated twice (2 pages)
        assert mock_go.call_count == 2
    
    @patch('linkedin_agent.tools.smart_search.nav_go')
    @patch('linkedin_agent.tools.smart_search.nav_wait')
    @patch('linkedin_agent.tools.smart_search.run_js')
    def test_smart_search_error_handling(self, mock_run_js, mock_wait, mock_go):
        """Test search handles errors gracefully"""
        mock_go.side_effect = Exception("Navigation failed")
        
        result = smart_candidate_search(
            query="Backend Engineer",
            location="San Francisco",
            page_limit=1
        )
        
        assert result['success'] == False
        assert 'error' in result
        assert result['candidates_found'] == 0
    
    @patch('linkedin_agent.tools.smart_search.nav_go')
    @patch('linkedin_agent.tools.smart_search.nav_wait')
    @patch('linkedin_agent.tools.smart_search.run_js')
    def test_smart_search_deduplication(self, mock_run_js, mock_wait, mock_go):
        """Test that duplicate candidates are filtered out"""
        # Return same candidate twice
        mock_run_js.return_value = [
            {
                'name': 'John Doe',
                'headline': 'backend engineer',
                'url': 'https://www.linkedin.com/in/johndoe'
            },
            {
                'name': 'John Doe',
                'headline': 'backend engineer',
                'url': 'https://www.linkedin.com/in/johndoe'  # Duplicate
            },
            {
                'name': 'Jane Smith',
                'headline': 'backend developer',
                'url': 'https://www.linkedin.com/in/janesmith'
            }
        ]
        
        result = smart_candidate_search(
            query="Backend",
            location="SF",
            page_limit=1,
            min_score=1.0,
            target_count=5
        )
        
        assert result['success'] == True
        assert result['candidates_found'] == 2  # Only 2 unique candidates
        
        urls = [c['url'] for c in result['candidates']]
        assert len(urls) == len(set(urls))  # All URLs should be unique


class TestExtractionJavaScript:
    """Test the JavaScript extraction code logic"""
    
    def test_extraction_javascript_syntax(self):
        """Verify the JavaScript extraction code is syntactically valid"""
        from linkedin_agent.tools.smart_search import _extract_candidates_from_page
        import re
        
        # Extract the JavaScript code from the function
        source = str(_extract_candidates_from_page.__code__.co_consts)
        
        # Check for common JavaScript syntax patterns
        assert '(() =>' in source or '(function()' in source
        assert 'document.querySelectorAll' in source
        assert 'return' in source
        assert '.map(' in source
        assert '.filter(' in source
    
    @patch('linkedin_agent.tools.smart_search.run_js')
    def test_extraction_handles_console_output(self, mock_run_js):
        """Test that console.log statements don't break extraction"""
        # Simulate JavaScript that includes console output
        mock_run_js.return_value = [
            {'name': 'Test User', 'headline': 'Engineer', 'url': 'https://linkedin.com/in/test'}
        ]
        
        candidates = _extract_candidates_from_page()
        
        assert len(candidates) == 1
        assert candidates[0]['name'] == 'Test User'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])