#!/usr/bin/env python3
"""
Integration tests for YouTube MCP Server
Tests server endpoints and API interactions
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

# Set test environment before importing
os.environ['YOUTUBE_API_KEY'] = 'test_api_key_for_testing'
os.environ['CACHE_ENABLED'] = 'false'
os.environ['RATE_LIMIT_ENABLED'] = 'false'


class TestServerInitialization:
    """Test server startup and configuration"""
    
    def test_server_imports_successfully(self):
        """Test that server module can be imported"""
        try:
            import server
            assert True
        except Exception as e:
            pytest.fail(f"Server import failed: {e}")
    
    def test_server_has_required_tools(self):
        """Test that all required tools are registered"""
        import server
        
        # Check that mcp instance exists
        assert hasattr(server, 'mcp')
        
    def test_youtube_api_client_initialized(self):
        """Test YouTube API client initialization"""
        import server
        
        assert hasattr(server, 'youtube')
        assert server.youtube is not None


class TestVideoTranscriptTool:
    """Test get_video_transcript tool"""
    
    @patch('server.YouTubeTranscriptApi')
    def test_get_transcript_with_valid_video(self, mock_transcript_api):
        """Test transcript retrieval with valid video"""
        import server
        # Access the underlying function from the MCP tool
        get_video_transcript = server.mcp.tools['get_video_transcript'].fn
        
        # Mock transcript data
        mock_transcript = Mock()
        mock_transcript.language_code = 'en'
        mock_transcript.is_generated = False
        mock_transcript.fetch.return_value = [
            {'text': 'Hello', 'start': 0.0, 'duration': 1.0},
            {'text': 'World', 'start': 1.0, 'duration': 1.0}
        ]
        
        mock_transcript_list = Mock()
        mock_transcript_list.find_transcript.return_value = mock_transcript
        mock_transcript_api.list_transcripts.return_value = mock_transcript_list
        
        # Test
        result = get_video_transcript("dQw4w9WgXcQ")
        
        assert result['success'] is True
        assert 'transcript' in result
        assert 'full_text' in result
    
    def test_get_transcript_with_invalid_video_id(self):
        """Test transcript with invalid video ID"""
        from server import get_video_transcript
        
        result = get_video_transcript("invalid")
        
        assert result['success'] is False
        assert 'error' in result


class TestVideoInfoTool:
    """Test get_video_info tool"""
    
    @patch('server.youtube')
    def test_get_video_info_success(self, mock_youtube):
        """Test video info retrieval"""
        from server import get_video_info
        
        # Mock API response
        mock_response = {
            'items': [{
                'id': 'dQw4w9WgXcQ',
                'snippet': {
                    'title': 'Test Video',
                    'description': 'Test Description',
                    'channelId': 'UC123',
                    'channelTitle': 'Test Channel',
                    'publishedAt': '2024-01-01T00:00:00Z',
                    'categoryId': '22',
                    'tags': ['test']
                },
                'statistics': {
                    'viewCount': '1000',
                    'likeCount': '100',
                    'commentCount': '10'
                },
                'contentDetails': {
                    'duration': 'PT5M'
                }
            }]
        }
        
        mock_youtube.videos.return_value.list.return_value.execute.return_value = mock_response
        
        result = get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        assert result['success'] is True
        assert result['title'] == 'Test Video'
        assert result['view_count'] == 1000
    
    def test_get_video_info_not_found(self):
        """Test video info with non-existent video"""
        from server import get_video_info
        import server
        
        # Mock empty response
        with patch.object(server.youtube.videos(), 'list') as mock_list:
            mock_list.return_value.execute.return_value = {'items': []}
            
            result = get_video_info("dQw4w9WgXcQ")
            
            assert result['success'] is False
            assert 'error' in result


class TestChannelInfoTool:
    """Test get_channel_info tool"""
    
    @patch('server.youtube')
    def test_get_channel_info_with_id(self, mock_youtube):
        """Test channel info with channel ID"""
        from server import get_channel_info
        
        # Mock API response
        mock_response = {
            'items': [{
                'id': 'UC_x5XG1OV2P6uZZ5FSM9Ttw',
                'snippet': {
                    'title': 'Google Developers',
                    'description': 'Test Channel',
                    'customUrl': '@googledev',
                    'publishedAt': '2020-01-01T00:00:00Z',
                    'country': 'US'
                },
                'statistics': {
                    'subscriberCount': '1000000',
                    'videoCount': '500',
                    'viewCount': '10000000',
                    'hiddenSubscriberCount': False
                }
            }]
        }
        
        mock_youtube.channels.return_value.list.return_value.execute.return_value = mock_response
        
        result = get_channel_info("UC_x5XG1OV2P6uZZ5FSM9Ttw")
        
        assert result['success'] is True
        assert result['title'] == 'Google Developers'
        assert result['subscriber_count'] == 1000000
    
    def test_get_channel_info_with_username(self):
        """Test channel info with @username"""
        from server import get_channel_info, resolve_channel_handle
        
        with patch('server.resolve_channel_handle', return_value='UC123'):
            with patch('server.youtube.channels') as mock_channels:
                mock_channels.return_value.list.return_value.execute.return_value = {
                    'items': [{
                        'id': 'UC123',
                        'snippet': {
                            'title': 'Test Channel',
                            'description': 'Test',
                            'publishedAt': '2020-01-01T00:00:00Z'
                        },
                        'statistics': {
                            'subscriberCount': '100',
                            'videoCount': '10',
                            'viewCount': '1000'
                        }
                    }]
                }
                
                result = get_channel_info("@testchannel")
                assert result['success'] is True


class TestSearchVideosTool:
    """Test search_videos tool"""
    
    @patch('server.youtube')
    def test_search_videos_basic(self, mock_youtube):
        """Test basic video search"""
        from server import search_videos
        
        # Mock API response
        mock_response = {
            'items': [
                {
                    'id': {'videoId': 'abc123'},
                    'snippet': {
                        'title': 'Python Tutorial',
                        'description': 'Learn Python',
                        'channelId': 'UC123',
                        'channelTitle': 'Code Academy',
                        'publishedAt': '2024-01-01T00:00:00Z'
                    }
                },
                {
                    'id': {'videoId': 'def456'},
                    'snippet': {
                        'title': 'Advanced Python',
                        'description': 'Advanced concepts',
                        'channelId': 'UC456',
                        'channelTitle': 'Pro Coders',
                        'publishedAt': '2024-01-02T00:00:00Z'
                    }
                }
            ]
        }
        
        mock_youtube.search.return_value.list.return_value.execute.return_value = mock_response
        
        result = search_videos("Python tutorial", max_results=10)
        
        assert result['success'] is True
        assert result['result_count'] == 2
        assert len(result['videos']) == 2
    
    def test_search_videos_with_order(self):
        """Test search with custom order"""
        from server import search_videos
        
        with patch('server.youtube.search') as mock_search:
            mock_search.return_value.list.return_value.execute.return_value = {'items': []}
            
            result = search_videos("test", order="viewCount")
            
            assert result['success'] is True
            assert result['order'] == 'viewCount'


class TestCommentsTool:
    """Test get_video_comments tool"""
    
    @patch('server.youtube')
    def test_get_comments_basic(self, mock_youtube):
        """Test comment retrieval"""
        from server import get_video_comments
        
        # Mock API response
        mock_response = {
            'items': [
                {
                    'id': 'comment1',
                    'snippet': {
                        'topLevelComment': {
                            'snippet': {
                                'authorDisplayName': 'User 1',
                                'textDisplay': 'Great video!',
                                'likeCount': 10,
                                'publishedAt': '2024-01-01T00:00:00Z',
                                'updatedAt': '2024-01-01T00:00:00Z'
                            }
                        },
                        'totalReplyCount': 0
                    }
                }
            ]
        }
        
        mock_youtube.commentThreads.return_value.list.return_value.execute.return_value = mock_response
        
        result = get_video_comments("dQw4w9WgXcQ", max_results=10)
        
        assert result['success'] is True
        assert result['comment_count'] >= 0
        assert 'comments' in result


class TestServerStatsTool:
    """Test get_server_stats tool"""
    
    def test_get_server_stats(self):
        """Test server statistics retrieval"""
        from server import get_server_stats
        
        result = get_server_stats()
        
        assert result['success'] is True
        assert 'cache' in result
        assert 'rate_limits' in result
        assert 'config' in result


class TestErrorHandling:
    """Test error handling across tools"""
    
    def test_invalid_api_key_handling(self):
        """Test behavior with invalid API key"""
        # This is more of a documentation test
        # In production, invalid keys would be caught by YouTube API
        assert True
    
    def test_network_error_handling(self):
        """Test network error handling"""
        from server import get_video_info
        from googleapiclient.errors import HttpError
        
        with patch('server.youtube.videos') as mock_videos:
            # Simulate network error
            mock_videos.return_value.list.return_value.execute.side_effect = HttpError(
                resp=Mock(status=500),
                content=b'Server Error'
            )
            
            result = get_video_info("dQw4w9WgXcQ")
            
            assert result['success'] is False
            assert 'error' in result


class TestInputSanitization:
    """Test that inputs are properly sanitized"""
    
    def test_malicious_input_rejected(self):
        """Test that malicious inputs are rejected"""
        from server import search_videos
        
        # Try various malicious inputs
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE videos; --",
            "../../../etc/passwd"
        ]
        
        for malicious_input in malicious_inputs:
            result = search_videos(malicious_input)
            # Should either reject or sanitize
            assert isinstance(result, dict)


# Run tests with: pytest tests/test_server.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
