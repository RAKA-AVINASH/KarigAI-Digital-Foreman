from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
import uuid


class ContentType(Enum):
    VIDEO = 'video'
    TEXT = 'text'
    VOICE_NOTE = 'voice_note'
    IMAGE = 'image'


@dataclass
class KnowledgeEntry:
    entry_id: str
    user_id: str
    problem_description: str
    solution_description: str
    content_type: ContentType
    content_url: str
    trade_type: str
    language: str
    tags: List[str] = field(default_factory=list)
    quality_score: float = 0.5
    upvotes: int = 0
    downvotes: int = 0
    views: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'entry_id': self.entry_id,
            'user_id': self.user_id,
            'problem_description': self.problem_description,
            'solution_description': self.solution_description,
            'content_type': self.content_type.value,
            'content_url': self.content_url,
            'trade_type': self.trade_type,
            'language': self.language,
            'tags': self.tags,
            'quality_score': self.quality_score,
            'upvotes': self.upvotes,
            'downvotes': self.downvotes,
            'views': self.views,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class SearchResults:
    entries: List[KnowledgeEntry]
    total_count: int


@dataclass
class UserReputation:
    user_id: str
    total_contributions: int = 0
    helpful_contributions: int = 0
    reputation_score: float = 0.0
    level: str = 'beginner'
    badges: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'total_contributions': self.total_contributions,
            'helpful_contributions': self.helpful_contributions,
            'reputation_score': self.reputation_score,
            'level': self.level,
            'badges': self.badges
        }


class CommunityKnowledgeService:
    def __init__(self):
        self.knowledge_base: Dict[str, KnowledgeEntry] = {}
        self.user_reputations: Dict[str, UserReputation] = {}
        self.user_votes: Dict[str, Dict[str, bool]] = {}
    
    def add_solution(self, user_id: str, problem_description: str, solution_description: str,
                    content_type: ContentType, content_url: str, trade_type: str, language: str) -> KnowledgeEntry:
        entry_id = str(uuid.uuid4())
        tags = self._generate_tags(problem_description, solution_description, trade_type)
        entry = KnowledgeEntry(entry_id=entry_id, user_id=user_id, problem_description=problem_description,
                              solution_description=solution_description, content_type=content_type,
                              content_url=content_url, trade_type=trade_type, language=language, tags=tags)
        self.knowledge_base[entry_id] = entry
        self._update_user_contributions(user_id)
        return entry
    
    def _generate_tags(self, problem: str, solution: str, trade_type: str) -> List[str]:
        tags = [trade_type]
        keywords = ['water', 'leak', 'pipe', 'electrical', 'wire', 'circuit', 'door', 'hinge', 'fix', 'repair', 'replace', 'tighten']
        text = f'{problem} {solution}'.lower()
        for keyword in keywords:
            if keyword in text:
                tags.append(keyword)
        return list(set(tags))
    
    def search_solutions(self, problem_query: str, trade_type: Optional[str] = None,
                        language: Optional[str] = None, min_quality_score: float = 0.0, limit: int = 10) -> SearchResults:
        query_lower = problem_query.lower()
        results = []
        for entry in self.knowledge_base.values():
            if trade_type and entry.trade_type != trade_type:
                continue
            if language and entry.language != language:
                continue
            if entry.quality_score < min_quality_score:
                continue
            if (query_lower in entry.problem_description.lower() or query_lower in entry.solution_description.lower() or
                any(query_lower in tag.lower() for tag in entry.tags)):
                results.append(entry)
        results.sort(key=lambda e: (e.quality_score, e.views), reverse=True)
        return SearchResults(entries=results[:limit], total_count=len(results))
    
    def rate_solution(self, entry_id: str, user_id: str, is_helpful: bool) -> KnowledgeEntry:
        if entry_id not in self.knowledge_base:
            raise ValueError(f'Entry {entry_id} not found')
        entry = self.knowledge_base[entry_id]
        if user_id not in self.user_votes:
            self.user_votes[user_id] = {}
        if is_helpful:
            entry.upvotes += 1
        else:
            entry.downvotes += 1
        self.user_votes[user_id][entry_id] = is_helpful
        total_votes = entry.upvotes + entry.downvotes
        if total_votes > 0:
            entry.quality_score = entry.upvotes / total_votes
        entry.updated_at = datetime.now()
        if is_helpful:
            self._update_helpful_contributions(entry.user_id)
        return entry
    
    def increment_views(self, entry_id: str) -> None:
        if entry_id in self.knowledge_base:
            self.knowledge_base[entry_id].views += 1
            self.knowledge_base[entry_id].updated_at = datetime.now()
    
    def get_user_reputation(self, user_id: str) -> UserReputation:
        if user_id not in self.user_reputations:
            self.user_reputations[user_id] = UserReputation(user_id=user_id)
        reputation = self.user_reputations[user_id]
        if reputation.total_contributions > 0:
            reputation.reputation_score = (reputation.helpful_contributions / reputation.total_contributions) * 100.0
        reputation.level = self._calculate_level(reputation)
        reputation.badges = self._calculate_badges(reputation)
        return reputation
    
    def _update_user_contributions(self, user_id: str) -> None:
        if user_id not in self.user_reputations:
            self.user_reputations[user_id] = UserReputation(user_id=user_id)
        self.user_reputations[user_id].total_contributions += 1
    
    def _update_helpful_contributions(self, user_id: str) -> None:
        if user_id not in self.user_reputations:
            self.user_reputations[user_id] = UserReputation(user_id=user_id)
        self.user_reputations[user_id].helpful_contributions += 1
    
    def _calculate_level(self, reputation: UserReputation) -> str:
        score = reputation.reputation_score
        contributions = reputation.total_contributions
        if contributions >= 50 and score >= 80:
            return 'master'
        elif contributions >= 20 and score >= 70:
            return 'expert'
        elif contributions >= 10 and score >= 60:
            return 'advanced'
        elif contributions >= 5:
            return 'intermediate'
        else:
            return 'beginner'
    
    def _calculate_badges(self, reputation: UserReputation) -> List[str]:
        badges = []
        if reputation.total_contributions >= 10:
            badges.append('contributor')
        if reputation.total_contributions >= 50:
            badges.append('expert_contributor')
        if reputation.helpful_contributions >= 20:
            badges.append('helpful_expert')
        if reputation.reputation_score >= 90:
            badges.append('quality_master')
        return badges
    
    def get_trending_solutions(self, trade_type: Optional[str] = None, limit: int = 10, days: int = 30) -> List[KnowledgeEntry]:
        entries = list(self.knowledge_base.values())
        if trade_type:
            entries = [e for e in entries if e.trade_type == trade_type]
        entries.sort(key=lambda e: (e.views + e.upvotes * 2, e.quality_score), reverse=True)
        return entries[:limit]
