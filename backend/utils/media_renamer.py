from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set
from loguru import logger
import re
import time
import yaml
from pathlib import Path

class MediaType(Enum):
    """媒体类型"""
    TV_SERIES = "tv_series"
    MOVIE = "movie"
    VARIETY_SHOW = "variety_show"
    DOCUMENTARY = "documentary"
    ANIME = "anime"
    UNKNOWN = "unknown"

class QualityLevel(Enum):
    """画质等级"""
    SD = "480p"
    HD = "720p"
    FHD = "1080p"
    UHD = "2160p"
    UNKNOWN = "unknown"

@dataclass
class MediaInfo:
    """媒体信息数据类"""
    title: str = ""
    original_filename: str = ""
    media_type: MediaType = MediaType.UNKNOWN
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: str = ""
    base_episode: Optional[int] = None  # 综艺节目的原始期数（如第8期的8）
    part_suffix: str = ""  # 综艺节目的上中下标识
    quality: QualityLevel = QualityLevel.UNKNOWN
    source: str = ""  # WEB-DL, BluRay, HDTV等
    codec: str = ""   # H264, H265, x264等
    audio: str = ""   # AAC, DTS, AC3等
    language: str = ""
    subtitle: str = ""
    group: str = ""   # 发布组
    extension: str = ""
    tags: Set[str] = field(default_factory=set)

    def update(self, data: Dict[str, Any]):
        """更新媒体信息"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

class MediaAnalyzer:
    """媒体文件分析器 - 处理各种规范和不规范的文件名"""

    def __init__(self):
        # 视频格式
        self.video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.rmvb'}

        # 画质标识
        self.quality_patterns = {
            r'2160p|4K|UHD': QualityLevel.UHD,
            r'1080p|FHD': QualityLevel.FHD,
            r'720p|HD': QualityLevel.HD,
            r'480p|SD': QualityLevel.SD
        }

        # 来源标识
        self.source_patterns = [
            'WEB-DL', 'WEBRip', 'BluRay', 'BDRip', 'DVDRip', 'HDTV', 'PDTV',
            'CAM', 'TS', 'TC', 'SCR', 'R5', 'DVDScr'
        ]

        # 编码标识
        self.codec_patterns = [
            'H264', 'H.264', 'x264', 'H265', 'H.265', 'x265', 'HEVC',
            'XviD', 'DivX', 'VP9', 'AV1'
        ]

        # 音频标识
        self.audio_patterns = [
            'AAC', 'AC3', 'DTS', 'DTS-HD', 'TrueHD', 'FLAC', 'MP3',
            'Atmos', 'DTS-X', '5.1', '7.1', '2.0'
        ]

        # 语言标识
        self.language_patterns = {
            'chinese': ['中文', '国语', '普通话', '粤语', 'Chinese', 'Mandarin', 'Cantonese'],
            'english': ['英语', 'English', 'ENG'],
            'japanese': ['日语', 'Japanese', 'JAP'],
            'korean': ['韩语', 'Korean', 'KOR']
        }

        # 字幕标识
        self.subtitle_patterns = [
            '中字', '英字', '双字', '内嵌', '外挂', 'SUB', 'DUB',
            '简体', '繁体', '中英', '多语'
        ]

        # 不规范文件名的处理策略 - 按优先级排序，更具体的模式在前
        # 使用 OrderedDict 确保匹配顺序
        from collections import OrderedDict
        self.irregular_patterns = OrderedDict([
            # 纯数字文件名 (1.mp4, 01.mp4, 001.mp4)
            ('pure_number', r'^(\d{1,3})\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 通用集数+画质格式 - 支持各种分隔符和集数标识
            # 匹配: 前缀[分隔符]集数标识[分隔符]画质[分隔符后缀].扩展名
            # 例如: 萨达卡斯柯 E01 4k.mp4, show+02+1080p.mp4, series-S01E03-720p-final.mp4
            ('universal_episode_quality', r'^(.+?)[\s\-_+.]*(?:S\d{1,2})?[Ee]?(\d{1,3})[\s\-_+.]*(?:1080p|720p|480p|4K|2160p|UHD|HD|FHD|SD)[\s\-_+.]*.*?\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 更精确的通用模式 - 分别捕获画质
            ('universal_episode_quality_precise', r'^(.+?)[\s\-_+.]*(?:S\d{1,2})?[Ee]?(\d{1,3})[\s\-_+.]*(1080p|720p|480p|4K|2160p|UHD|HD|FHD|SD)[\s\-_+.]*.*?\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 综艺节目日期+期数格式 - 超宽泛匹配（优化版）
            # 支持: saa.24.02.22.第9期.mp4, show 25 03 14第十期.mp4, prefix-2025.03.14-第8期中.mp4 等
            # 匹配任意前缀 + 日期(各种分隔符) + 期数
            ('variety_date_episode', r'^[^第]*?(\d{2,4})[\s.\-_/]*(\d{1,2})[\s.\-_/]*(\d{1,2})[\s.\-_/]*第([一二三四五六七八九十百千万\d]{1,10})[期话]([上中下]?)[^.]*\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 综艺节目日期+特殊版本 - 超宽泛匹配（优化版）
            # 支持: saa.25.03.14纯享版.mp4, show 2025 06 14花絮版.mp4 等
            ('variety_date_special', r'^[^纯花幕加完精未]*?(\d{2,4})[\s.\-_/]*(\d{1,2})[\s.\-_/]*(\d{1,2})[\s.\-_/]*(纯享版|花絮版|幕后版|加更版|完整版|精华版|未删减版)[^.]*\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 简单数字+扩展名 (第1集.mp4, 第01集.mp4, 第001集.mp4)
            ('simple_episode', r'^第?(\d{1,3})[集期话]?\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 中文数字 (一.mp4, 第一集.mp4)
            ('chinese_number', r'^第?([一二三四五六七八九十百]+)[集期话]?\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 英文序号 (Episode1.mp4, EP01.mp4, E01.mp4)
            ('english_episode', r'^(Episode|EP|E)(\d{1,3})\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 标准格式带中文描述 (深情眼 - S01E11 - 第 11 集.mkv)
            ('standard_with_chinese', r'^(.+?)\s*-\s*[Ss](\d{1,2})[Ee](\d{1,3})\s*-\s*第\s*(\d+)\s*[集期话]?\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 混合格式 (剧名01.mp4, 剧名第1集.mp4) - 只匹配真正的中文集数格式
            ('mixed_format', r'^(.+?)第(\d{1,3})[集期话]\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 剧名+数字格式 (深情眼01.mkv, 剧集名02.mp4)
            ('title_number', r'^([^\d]+)(\d{1,3})\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 日期格式 (20231225.mp4, 2023-12-25.mp4)
            ('date_format', r'^(\d{4}[-_]?\d{2}[-_]?\d{2})\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 时间戳格式 (20231225_1400.mp4)
            ('timestamp_format', r'^(\d{4}[-_]?\d{2}[-_]?\d{2}[-_]?\d{4})\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$'),

            # 随机字符 (abc123.mp4, random_name.mp4) - 最后匹配，避免误匹配标准格式
            ('random_name', r'^([a-zA-Z0-9_\-]+)\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$')
        ])

        # 中文数字映射
        self.chinese_numbers = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
            '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
            '二十一': 21, '二十二': 22, '二十三': 23, '二十四': 24, '二十五': 25,
            '三十': 30, '四十': 40, '五十': 50, '六十': 60, '七十': 70,
            '八十': 80, '九十': 90, '一百': 100
        }
    
    def analyze(self, filename: str, context: Dict[str, Any] = None) -> MediaInfo:
        """分析媒体文件信息 - 支持上下文信息"""
        info = MediaInfo(original_filename=filename)
        context = context or {}

        # 基础信息提取
        info.extension = self._extract_extension(filename)
        if info.extension not in self.video_extensions:
            return info  # 非视频文件

        # 首先尝试处理不规范文件名
        irregular_result = self._handle_irregular_filename(filename, context)
        if irregular_result:
            info.update(irregular_result)
            info.media_type = self._determine_media_type(info)
            return info

        # 标准文件名处理流程
        clean_name = self._clean_filename(filename)

        # 提取各种信息
        info.title = self._extract_title(clean_name)
        info.year = self._extract_year(clean_name)
        info.season, info.episode = self._extract_season_episode(clean_name)
        info.quality = self._extract_quality(clean_name)
        info.source = self._extract_source(clean_name)
        info.codec = self._extract_codec(clean_name)
        info.audio = self._extract_audio(clean_name)
        info.language = self._extract_language(clean_name)
        info.subtitle = self._extract_subtitle(clean_name)
        info.group = self._extract_group(clean_name)
        info.media_type = self._determine_media_type(info)

        return info

    def _handle_irregular_filename(self, filename: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理不规范的文件名"""
        filename_lower = filename.lower()

        # 检查各种不规范模式
        for pattern_name, pattern in self.irregular_patterns.items():
            match = re.match(pattern, filename_lower, re.IGNORECASE)
            if match:
                return self._process_irregular_match(pattern_name, match, filename, context)

        return None

    def _process_irregular_match(self, pattern_name: str, match: re.Match,
                                filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理不规范文件名的匹配结果"""
        result = {}

        if pattern_name == 'pure_number':
            # 纯数字文件名: 1.mp4, 01.mp4, 001.mp4
            episode_num = int(match.group(1))
            result.update({
                'episode': episode_num,
                'title': context.get('series_title', f"Series_{episode_num:02d}"),
                'season': context.get('season', 1),
                'extension': f".{match.group(2)}"
            })

        elif pattern_name in ['universal_episode_quality', 'universal_episode_quality_precise']:
            # 通用集数+画质格式处理
            # 支持各种分隔符: 萨达卡斯柯 E01 4k.mp4, show+02+1080p.mp4, series-S01E03-720p.mp4

            if pattern_name == 'universal_episode_quality_precise':
                # 精确模式，分别捕获画质
                prefix = match.group(1).strip()
                episode_num = int(match.group(2))
                quality_str = match.group(3)
                extension = f".{match.group(4)}"
            else:
                # 基础模式，需要重新解析画质
                prefix = match.group(1).strip()
                episode_num = int(match.group(2))
                extension = f".{match.group(3)}"
                # 从原始文件名中提取画质
                quality_match = re.search(r'(1080p|720p|480p|4K|2160p|UHD|HD|FHD|SD)', match.group(0), re.IGNORECASE)
                quality_str = quality_match.group(1) if quality_match else 'UNKNOWN'

            # 映射画质标识到QualityLevel枚举 (不区分大小写)
            quality_mapping = {
                '4k': QualityLevel.UHD, '4K': QualityLevel.UHD,
                '2160p': QualityLevel.UHD,
                'uhd': QualityLevel.UHD, 'UHD': QualityLevel.UHD,
                '1080p': QualityLevel.FHD,
                'fhd': QualityLevel.FHD, 'FHD': QualityLevel.FHD,
                '720p': QualityLevel.HD,
                'hd': QualityLevel.HD, 'HD': QualityLevel.HD,
                '480p': QualityLevel.SD,
                'sd': QualityLevel.SD, 'SD': QualityLevel.SD
            }

            # 如果有自定义标题，使用自定义标题；否则尝试从前缀推断
            title = context.get('series_title')
            if not title:
                # 清理前缀作为标题 - 移除各种分隔符和集数标识
                clean_prefix = re.sub(r'[\s\-_+.]*(?:S\d{1,2})?[Ee]?\d{1,3}.*$', '', prefix, flags=re.IGNORECASE)
                title = clean_prefix.replace('_', ' ').replace('-', ' ').replace('+', ' ').strip()
                if not title or len(title) < 2:
                    title = f"Series_{episode_num:02d}"

            result.update({
                'episode': episode_num,
                'title': title,
                'season': context.get('season', 1),
                'quality': quality_mapping.get(quality_str.lower(), QualityLevel.UNKNOWN),
                'extension': extension
            })

        elif pattern_name == 'variety_date_episode':
            # 综艺节目日期+期数格式: saa.24.02.22.第9期.mp4, show 25 03 14第十期.mp4
            year_str = match.group(1)
            month_str = match.group(2)
            day_str = match.group(3)
            episode_str = match.group(4)  # 可能是数字或中文数字
            part_indicator = match.group(5)  # 上中下
            extension = f".{match.group(6)}"

            # 处理期数：支持阿拉伯数字和中文数字
            if episode_str.isdigit():
                # 阿拉伯数字
                base_episode_num = int(episode_str)
            else:
                # 中文数字，使用现有的转换方法
                base_episode_num = self._convert_chinese_number(episode_str)

            # 保留原始期数，不做特殊计算
            episode_num = base_episode_num
            part_suffix = part_indicator  # 直接保留上中下标识

            # 解析日期信息
            # 处理两位年份
            if len(year_str) == 2:
                year = 2000 + int(year_str)
            else:
                year = int(year_str)
            month = int(month_str)
            day = int(day_str)

            result.update({
                'episode': episode_num,
                'title': context.get('series_title', "Variety Show"),
                'season': context.get('season', 1),
                'media_type': MediaType.TV_SERIES,  # 综艺按剧集处理
                'year': year,
                'extension': extension,
                'base_episode': base_episode_num,  # 保存原始期数
                'part_suffix': part_suffix  # 保存上中下标识
            })

        elif pattern_name == 'variety_date_special':
            # 综艺节目日期+特殊版本: saa.25.06.14纯享版.mp4, show 2025 07 15花絮版.mp4
            year_str = match.group(1)
            month_str = match.group(2)
            day_str = match.group(3)
            special_type = match.group(4)
            extension = f".{match.group(5)}"

            # 解析日期信息
            # 处理两位年份
            if len(year_str) == 2:
                year = 2000 + int(year_str)
            else:
                year = int(year_str)
            month = int(month_str)
            day = int(day_str)

            # 特殊版本不设置集数，保留版本标识
            episode_num = None  # 特殊版本没有集数概念

            result.update({
                'episode': episode_num,  # None for special versions
                'title': context.get('series_title', "Variety Show"),
                'season': context.get('season', 1),
                'media_type': MediaType.TV_SERIES,  # 综艺按剧集处理
                'year': year,
                'extension': extension,
                'base_episode': None,  # 特殊版本没有原始期数
                'part_suffix': special_type  # 将特殊版本标识保存到part_suffix
            })

        elif pattern_name == 'simple_episode':
            # 简单集数: 第1集.mp4, 第01集.mp4
            episode_num = int(match.group(1))
            result.update({
                'episode': episode_num,
                'title': context.get('series_title', "Unknown Series"),
                'season': context.get('season', 1),
                'extension': f".{match.group(2)}"
            })

        elif pattern_name == 'chinese_number':
            # 中文数字: 一.mp4, 第一集.mp4
            chinese_num = match.group(1)
            episode_num = self._convert_chinese_number(chinese_num)
            result.update({
                'episode': episode_num,
                'title': context.get('series_title', "Unknown Series"),
                'season': context.get('season', 1),
                'extension': f".{match.group(2)}"
            })

        elif pattern_name == 'english_episode':
            # 英文集数: Episode1.mp4, EP01.mp4, E01.mp4
            episode_num = int(match.group(2))
            result.update({
                'episode': episode_num,
                'title': context.get('series_title', "Unknown Series"),
                'season': context.get('season', 1),
                'extension': f".{match.group(3)}"
            })

        elif pattern_name == 'mixed_format':
            # 混合格式: 剧名01.mp4, 剧名第1集.mp4
            title_part = match.group(1).strip() 
            # 清理标题中的多余点号
            title_part = re.sub(r'\.+$', '', title_part)  # 移除结尾的点号
            episode_num = int(match.group(2))
            result.update({
                'episode': episode_num,
                'title': title_part or context.get('series_title', "Unknown Series"),
                'season': context.get('season', 1),
                'extension': f".{match.group(3)}"
            })

        elif pattern_name == 'standard_with_chinese':
            # 标准格式带中文描述: 深情眼 - S01E11 - 第 11 集.mkv
            title_part = match.group(1).strip()
            season_num = int(match.group(2))
            episode_num = int(match.group(3))
            chinese_episode = int(match.group(4))  # 中文集数，用于验证
            extension = f".{match.group(5)}"

            # 验证标准格式的集数和中文集数是否一致
            if episode_num != chinese_episode:
                logger.warning(f"集数不一致: S{season_num:02d}E{episode_num:02d} vs 第{chinese_episode}集")

            result.update({
                'title': title_part,
                'season': season_num,
                'episode': episode_num,
                'extension': extension,
                'media_type': MediaType.TV_SERIES
            })

        elif pattern_name == 'title_number':
            # 剧名+数字格式: 深情眼01.mkv, 剧集名02.mp4
            title_part = match.group(1).strip()
            episode_num = int(match.group(2))
            extension = f".{match.group(3)}"

            result.update({
                'title': title_part,
                'season': context.get('season', 1),
                'episode': episode_num,
                'extension': extension,
                'media_type': MediaType.TV_SERIES
            })

        elif pattern_name == 'date_format':
            # 日期格式: 20231225.mp4, 2023-12-25.mp4
            date_str = match.group(1)
            # 解析日期
            clean_date = re.sub(r'[-_]', '', date_str)
            if len(clean_date) == 8:
                year = int(clean_date[:4])
                month = int(clean_date[4:6])
                day = int(clean_date[6:8])
                result.update({
                    'title': context.get('series_title', "Daily Show"),
                    'year': year,
                    'episode': day,  # 使用日期作为集数
                    'extension': f".{match.group(2)}"
                })

        elif pattern_name == 'timestamp_format':
            # 时间戳格式: 20231225_1400.mp4
            timestamp_str = match.group(1)
            clean_timestamp = re.sub(r'[-_]', '', timestamp_str)
            if len(clean_timestamp) >= 8:
                year = int(clean_timestamp[:4])
                month = int(clean_timestamp[4:6])
                day = int(clean_timestamp[6:8])
                result.update({
                    'title': context.get('series_title', "Timestamped Show"),
                    'year': year,
                    'episode': day,
                    'extension': f".{match.group(2)}"
                })

        elif pattern_name == 'random_name':
            # 随机命名: abc123.mp4, random_name.mp4
            random_name = match.group(1)

            # 检查是否包含标准季集格式，如果是则不应该被random_name处理
            if re.search(r'[Ss]\d{1,2}[Ee]\d{1,3}', random_name):
                # 包含标准格式，返回None让其进入标准处理流程
                return None

            # 尝试从文件名中提取数字作为集数
            numbers = re.findall(r'\d+', random_name)
            episode_num = int(numbers[-1]) if numbers else 1

            result.update({
                'episode': episode_num,
                'title': context.get('series_title', "Unknown Series"),
                'season': context.get('season', 1),
                'extension': f".{match.group(2)}"
            })

        return result

    def _convert_chinese_number(self, chinese_num: str) -> int:
        """转换中文数字为阿拉伯数字"""
        if chinese_num in self.chinese_numbers:
            return self.chinese_numbers[chinese_num]

        # 处理复合中文数字
        if '十' in chinese_num:
            if chinese_num == '十':
                return 10
            elif chinese_num.startswith('十'):
                # 十一、十二等
                return 10 + self.chinese_numbers.get(chinese_num[1:], 0)
            elif chinese_num.endswith('十'):
                # 二十、三十等
                return self.chinese_numbers.get(chinese_num[:-1], 0) * 10
            else:
                # 二十一、三十五等
                parts = chinese_num.split('十')
                if len(parts) == 2:
                    tens = self.chinese_numbers.get(parts[0], 0) * 10
                    ones = self.chinese_numbers.get(parts[1], 0)
                    return tens + ones

        return 1  # 默认返回1
    
    def _clean_filename(self, filename: str) -> str:
        """清理文件名，移除扩展名和特殊字符"""
        name = Path(filename).stem
        # 替换常见分隔符为空格
        name = re.sub(r'[._\-\[\](){}]', ' ', name)
        # 合并多个空格
        name = re.sub(r'\s+', ' ', name)
        return name.strip()
    
    def _extract_extension(self, filename: str) -> str:
        """提取文件扩展名"""
        return Path(filename).suffix.lower()
    
    def _extract_title(self, clean_name: str) -> str:
        """提取标题 - 智能识别主标题"""
        # 移除年份、季集信息、画质等技术信息
        title = clean_name

        # 移除年份
        title = re.sub(r'\b(19|20)\d{2}\b', '', title)

        # 移除季集信息
        title = re.sub(r'[\.\s]*[Ss]\d{1,2}[Ee]\d{1,3}[\.\s]*', '', title)
        title = re.sub(r'[\.\s]*第\s*\d+\s*[季集期话][\.\s]*', '', title)
        title = re.sub(r'[\.\s]*(Season|Episode)\s*\d+[\.\s]*', '', title, flags=re.IGNORECASE)

        # 移除画质信息
        for pattern in self.quality_patterns.keys():
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        # 移除来源信息
        for source in self.source_patterns:
            title = re.sub(rf'\b{re.escape(source)}\b', '', title, flags=re.IGNORECASE)

        # 移除编码信息
        for codec in self.codec_patterns:
            title = re.sub(rf'\b{re.escape(codec)}\b', '', title, flags=re.IGNORECASE)

        # 移除多余的点号和空格
        title = re.sub(r'\.+', '.', title)  # 多个点号合并为一个
        title = re.sub(r'^\.|\.+$', '', title)  # 移除开头和结尾的点号
        title = re.sub(r'\s+', ' ', title).strip()  # 多个空格合并为一个

        return title if title else "Unknown"
    
    def _extract_year(self, clean_name: str) -> Optional[int]:
        """提取年份"""
        # 查找4位年份
        matches = re.findall(r'\b(19[5-9]\d|20[0-4]\d)\b', clean_name)
        if matches:
            return int(matches[0])
        return None
    
        """提取季数和集数"""
    def _extract_season_episode(self, clean_name: str) -> Tuple[Optional[int], Optional[int]]:
        season, episode = None, None
        
        # 标准格式 S01E01
        match = re.search(r'\b[Ss](\d{1,2})[Ee](\d{1,3})\b', clean_name)
        if match:
            season = int(match.group(1))
            episode = int(match.group(2))
            return season, episode
        
        # 中文格式
        season_match = re.search(r'第\s*(\d+)\s*季', clean_name)
        if season_match:
            season = int(season_match.group(1))
        
        episode_match = re.search(r'第\s*(\d+)\s*[集期话]', clean_name)
        if episode_match:
            episode = int(episode_match.group(1))
        
        # 英文格式
        if not season:
            season_match = re.search(r'\bSeason\s*(\d+)\b', clean_name, re.IGNORECASE)
            if season_match:
                season = int(season_match.group(1))
        
        if not episode:
            episode_match = re.search(r'\bEpisode\s*(\d+)\b', clean_name, re.IGNORECASE)
            if episode_match:
                episode = int(episode_match.group(1))
        
        return season, episode
    
    def _extract_quality(self, clean_name: str) -> QualityLevel:
        """提取画质信息"""
        for pattern, quality in self.quality_patterns.items():
            if re.search(pattern, clean_name, re.IGNORECASE):
                return quality
        return QualityLevel.UNKNOWN
    
    def _extract_source(self, clean_name: str) -> str:
        """提取来源信息"""
        for source in self.source_patterns:
            if re.search(rf'\b{re.escape(source)}\b', clean_name, re.IGNORECASE):
                return source
        return ""
    
    def _extract_codec(self, clean_name: str) -> str:
        """提取编码信息"""
        for codec in self.codec_patterns:
            if re.search(rf'\b{re.escape(codec)}\b', clean_name, re.IGNORECASE):
                return codec
        return ""
    
    def _extract_audio(self, clean_name: str) -> str:
        """提取音频信息"""
        for audio in self.audio_patterns:
            if re.search(rf'\b{re.escape(audio)}\b', clean_name, re.IGNORECASE):
                return audio
        return ""
    
    def _extract_language(self, clean_name: str) -> str:
        """提取语言信息"""
        for lang, patterns in self.language_patterns.items():
            for pattern in patterns:
                if pattern in clean_name:
                    return lang
        return ""
    
    def _extract_subtitle(self, clean_name: str) -> str:
        """提取字幕信息"""
        for sub in self.subtitle_patterns:
            if sub in clean_name:
                return sub
        return ""
    
    def _extract_group(self, clean_name: str) -> str:
        """提取发布组信息"""
        # 通常在文件名末尾的方括号或圆括号中
        match = re.search(r'[\[\(]([^[\]()]+)[\]\)]$', clean_name)
        if match:
            group = match.group(1).strip()
            # 过滤掉画质、编码等技术信息
            if not any(tech in group.upper() for tech in ['1080P', '720P', 'H264', 'X264', 'AAC']):
                return group
        return ""
    
    def _determine_media_type(self, info: MediaInfo) -> MediaType:
        """判断媒体类型"""
        # 有季集信息的通常是电视剧
        if info.season is not None or info.episode is not None:
            # 检查是否为综艺节目
            variety_keywords = ['综艺', '节目', '秀', 'Show', '期']
            if any(keyword in info.title for keyword in variety_keywords):
                return MediaType.VARIETY_SHOW
            
            # 检查是否为动漫
            anime_keywords = ['动漫', '动画', 'Anime', '番']
            if any(keyword in info.title for keyword in anime_keywords):
                return MediaType.ANIME
            
            return MediaType.TV_SERIES
        
        # 检查是否为纪录片
        doc_keywords = ['纪录片', 'Documentary', '记录', '探索']
        if any(keyword in info.title for keyword in doc_keywords):
            return MediaType.DOCUMENTARY
        
        # 默认为电影
        return MediaType.MOVIE

class ContextInferrer:
    """上下文推断器 - 从文件列表和目录结构推断上下文信息"""

    def __init__(self):
        self.common_series_patterns = [
            # 常见电视剧关键词
            r'(第\d+季|Season\s*\d+|S\d+)',
            r'(剧集|电视剧|TV|Series)',
            r'(连续剧|电视连续剧)',
        ]

        self.common_variety_patterns = [
            r'(综艺|节目|秀|Show)',
            r'(第\d+期|期)',
            r'(访谈|脱口秀|真人秀)',
        ]

    def infer_context(self, filenames: List[str], directory_path: str = "") -> Dict[str, Any]:
        """从文件列表推断上下文信息"""
        context = {
            'series_title': None,
            'season': 1,
            'media_type': MediaType.UNKNOWN,
            'is_batch': len(filenames) > 1,
            'file_count': len(filenames)
        }

        if not filenames:
            return context

        # 从目录名推断标题
        if directory_path:
            dir_name = Path(directory_path).name
            context['series_title'] = self._extract_title_from_dirname(dir_name)
            context['season'] = self._extract_season_from_dirname(dir_name)

        # 分析文件名模式
        pattern_analysis = self._analyze_filename_patterns(filenames)

        # 如果没有从目录名获得标题，尝试从文件名推断
        if not context['series_title']:
            context['series_title'] = pattern_analysis.get('common_title')

        # 推断媒体类型
        context['media_type'] = pattern_analysis.get('media_type', MediaType.TV_SERIES)

        # 如果是连续的数字文件名，很可能是电视剧
        if pattern_analysis.get('is_sequential_numbers'):
            context['media_type'] = MediaType.TV_SERIES

        return context

    def _extract_title_from_dirname(self, dirname: str) -> Optional[str]:
        """从目录名提取标题"""
        # 清理目录名
        clean_name = dirname

        # 移除季数信息
        clean_name = re.sub(r'第\d+季|Season\s*\d+|S\d+', '', clean_name, flags=re.IGNORECASE)

        # 移除年份
        clean_name = re.sub(r'\b(19|20)\d{2}\b', '', clean_name)

        # 移除画质信息
        clean_name = re.sub(r'\b(480p|720p|1080p|2160p|4K|HD|FHD|UHD)\b', '', clean_name, flags=re.IGNORECASE)

        # 清理特殊字符
        clean_name = re.sub(r'[._\-\[\](){}]', ' ', clean_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()

        return clean_name if clean_name else None

    def _extract_season_from_dirname(self, dirname: str) -> int:
        """从目录名提取季数"""
        # 查找季数
        season_match = re.search(r'第(\d+)季|Season\s*(\d+)|S(\d+)', dirname, re.IGNORECASE)
        if season_match:
            for group in season_match.groups():
                if group:
                    return int(group)
        return 1

    def _analyze_filename_patterns(self, filenames: List[str]) -> Dict[str, Any]:
        """分析文件名模式"""
        analysis = {
            'common_title': None,
            'media_type': MediaType.UNKNOWN,
            'is_sequential_numbers': False,
            'has_episode_info': False
        }

        if not filenames:
            return analysis

        # 检查是否为连续数字文件名
        numbers = []
        for filename in filenames:
            # 提取文件名中的数字
            name_without_ext = Path(filename).stem
            number_matches = re.findall(r'\d+', name_without_ext)
            if number_matches:
                numbers.extend([int(n) for n in number_matches])

        if numbers:
            numbers.sort()
            # 检查是否连续
            is_sequential = all(numbers[i] == numbers[i-1] + 1 for i in range(1, len(numbers)))
            analysis['is_sequential_numbers'] = is_sequential

        # 尝试提取公共标题
        common_title = self._extract_common_title(filenames)
        if common_title:
            analysis['common_title'] = common_title

        # 检查是否包含集数信息
        episode_indicators = ['第', '集', '期', 'Episode', 'EP', 'E']
        has_episode = any(
            any(indicator in filename for indicator in episode_indicators)
            for filename in filenames
        )
        analysis['has_episode_info'] = has_episode

        # 推断媒体类型
        if has_episode or analysis['is_sequential_numbers']:
            # 检查是否为综艺节目
            variety_keywords = ['综艺', '节目', '秀', 'Show', '期']
            if any(keyword in ' '.join(filenames) for keyword in variety_keywords):
                analysis['media_type'] = MediaType.VARIETY_SHOW
            else:
                analysis['media_type'] = MediaType.TV_SERIES
        else:
            analysis['media_type'] = MediaType.MOVIE

        return analysis

    def _extract_common_title(self, filenames: List[str]) -> Optional[str]:
        """提取文件名的公共部分作为标题"""
        if not filenames:
            return None

        if len(filenames) == 1:
            # 单个文件，尝试提取标题
            filename = Path(filenames[0]).stem
            # 移除数字和常见后缀
            title = re.sub(r'\d+|第\d+集|第\d+期|Episode\d+|EP\d+|E\d+', '', filename)
            title = re.sub(r'[._\-\s]+', ' ', title).strip()
            return title if title else None

        # 多个文件，找公共前缀
        common_prefix = filenames[0]
        for filename in filenames[1:]:
            # 找到公共前缀
            i = 0
            while i < min(len(common_prefix), len(filename)) and common_prefix[i] == filename[i]:
                i += 1
            common_prefix = common_prefix[:i]

        # 清理公共前缀
        common_prefix = Path(common_prefix).stem if '.' in common_prefix else common_prefix
        common_prefix = re.sub(r'[._\-\s]+$', '', common_prefix).strip()

        return common_prefix if len(common_prefix) > 2 else None

class SmartBatchRenamer:
    """智能批量重命名器 - 处理各种不规范文件名的批量重命名"""

    def __init__(self):
        self.analyzer = MediaAnalyzer()
        self.formatter = MediaFormatter()
        self.context_inferrer = ContextInferrer()

    def batch_rename_with_context(self, filenames: List[str], directory_path: str = "",
                                 custom_title: str = None, custom_season: int = None) -> List[Dict[str, Any]]:
        """带上下文的批量重命名"""
        # 推断上下文
        context = self.context_inferrer.infer_context(filenames, directory_path)

        # 应用用户自定义设置
        if custom_title:
            context['series_title'] = custom_title
        if custom_season:
            context['season'] = custom_season

        results = []

        for i, filename in enumerate(filenames, 1):
            try:
                # 为每个文件添加索引信息
                file_context = context.copy()
                file_context['file_index'] = i

                # 分析文件
                media_info = self.analyzer.analyze(filename, file_context)

                # 如果没有检测到集数，使用文件索引
                if not media_info.episode:
                    media_info.episode = i

                # 格式化新文件名
                new_filename = self.formatter.format(media_info, template_name="simple")

                results.append({
                    'original': filename,
                    'renamed': new_filename,
                    'status': 'success',
                    'media_info': {
                        'title': media_info.title,
                        'season': media_info.season,
                        'episode': media_info.episode,
                        'media_type': media_info.media_type.value
                    }
                })

            except Exception as e:
                logger.error(f"重命名失败 {filename}: {e}")
                results.append({
                    'original': filename,
                    'renamed': filename,
                    'status': 'failed',
                    'error': str(e)
                })

        return results

    def preview_batch_rename(self, filenames: List[str], directory_path: str = "",
                           custom_title: str = None, custom_season: int = None,
                           style: str = "simple") -> Dict[str, Any]:
        """预览批量重命名结果"""
        context = self.context_inferrer.infer_context(filenames, directory_path)

        if custom_title:
            context['series_title'] = custom_title
        if custom_season:
            context['season'] = custom_season

        preview_results = []

        for i, filename in enumerate(filenames[:5], 1):  # 只预览前5个
            file_context = context.copy()
            file_context['file_index'] = i

            try:
                media_info = self.analyzer.analyze(filename, file_context)
                if not media_info.episode:
                    media_info.episode = i

                new_filename = self.formatter.format(media_info, template_name=style)

                preview_results.append({
                    'original': filename,
                    'renamed': new_filename
                })
            except Exception as e:
                preview_results.append({
                    'original': filename,
                    'renamed': f"ERROR: {str(e)}"
                })

        return {
            'context': context,
            'preview': preview_results,
            'total_files': len(filenames),
            'showing': min(5, len(filenames))
        }

    def preview_batch_rename_with_template(self, filenames: List[str], template: str,
                                         directory_path: str = "", custom_title: str = None) -> Dict[str, Any]:
        """使用指定模板预览批量重命名结果"""
        context = self.context_inferrer.infer_context(filenames, directory_path)

        if custom_title:
            context['series_title'] = custom_title

        preview_results = []

        for i, filename in enumerate(filenames[:5], 1):  # 只预览前5个
            file_context = context.copy()
            file_context['file_index'] = i

            try:
                media_info = self.analyzer.analyze(filename, file_context)
                if not media_info.episode:
                    media_info.episode = i

                new_filename = self.formatter.format(media_info, custom_template=template)

                preview_results.append({
                    'original': filename,
                    'renamed': new_filename
                })
            except Exception as e:
                preview_results.append({
                    'original': filename,
                    'renamed': f"错误: {str(e)}"
                })

        return {
            'context': context,
            'preview': preview_results,
            'total_files': len(filenames),
            'showing': min(5, len(filenames))
        }

class MediaFormatter:
    """媒体文件格式化器 - 根据不同类型生成标准化文件名，支持自定义模板"""

    def __init__(self):
        # 预定义的命名模板
        self.templates = {
            MediaType.TV_SERIES: "{title}.S{season:02d}E{episode:02d}.{quality}.{source}.{codec}.{extension}",
            MediaType.MOVIE: "{title}.{year}.{quality}.{source}.{codec}.{extension}",
            MediaType.VARIETY_SHOW: "{title}.{year}{month:02d}{day:02d}.第{base_episode}期{part_suffix}.{quality}.{extension}",
            MediaType.DOCUMENTARY: "{title}.{year}.{quality}.{source}.{extension}",
            MediaType.ANIME: "{title}.第{episode:02d}话.{quality}.{extension}"
        }

        # 简化模板（用于简洁命名）
        self.simple_templates = {
            MediaType.TV_SERIES: "{title}.S{season:02d}E{episode:02d}.{extension}",
            MediaType.MOVIE: "{title}.{year}.{extension}",
            MediaType.VARIETY_SHOW: "{title}.第{base_episode}期{part_suffix}.{extension}",
            MediaType.DOCUMENTARY: "{title}.{extension}",
            MediaType.ANIME: "{title}.第{episode:02d}话.{extension}"
        }

        # 中文描述模板（包含中文集数描述）
        self.chinese_templates = {
            MediaType.TV_SERIES: "{title} - S{season:02d}E{episode:02d} - 第 {episode} 集.{extension}",
            MediaType.MOVIE: "{title} - {year}年.{extension}",
            MediaType.VARIETY_SHOW: "{title} - 第{base_episode}期{part_suffix}.{extension}",
            MediaType.DOCUMENTARY: "{title} - 纪录片.{extension}",
            MediaType.ANIME: "{title} - 第{episode:02d}话.{extension}"
        }

        # 用户自定义模板存储
        self.custom_templates = {}

        # 可用的变量列表（用于模板验证和提示）
        self.available_variables = {
            'title': '标题',
            'season': '季数',
            'episode': '集数',
            'year': '年份',
            'quality': '画质',
            'source': '来源',
            'codec': '编码',
            'audio': '音频',
            'language': '语言',
            'subtitle': '字幕',
            'group': '发布组',
            'extension': '扩展名',
            'month': '月份',
            'day': '日期',
            'episode_title': '集标题'
        }

    def format(self, media_info: MediaInfo, template_name: str = "standard", custom_template: str = None) -> str:
        """格式化媒体文件名"""
        # 如果提供了自定义模板，优先使用
        if custom_template:
            template = custom_template
        elif template_name in self.custom_templates:
            # 使用用户保存的自定义模板
            template = self.custom_templates[template_name]
        else:
            # 使用预定义模板
            template = self._get_predefined_template(template_name, media_info.media_type)

        # 特殊处理综艺节目的特殊版本（如纯享版、花絮版等）
        if (media_info.media_type == MediaType.VARIETY_SHOW and
            media_info.base_episode is None and
            media_info.part_suffix):
            # 特殊版本使用不同的模板
            template = self._get_special_variety_template(template_name)

        # 准备格式化参数
        format_params = self._prepare_format_params(media_info)

        try:
            # 格式化文件名
            formatted_name = template.format(**format_params)

            # 清理文件名
            formatted_name = self._clean_formatted_name(formatted_name)

            return formatted_name
        except KeyError as e:
            logger.warning(f"格式化失败，缺少参数: {e}")
            return self._fallback_format(media_info)

    def _prepare_format_params(self, media_info: MediaInfo) -> Dict[str, Any]:
        """准备格式化参数"""
        params = {
            'title': media_info.title or "Unknown",
            'year': media_info.year or "",
            'season': media_info.season or 1,
            'episode': media_info.episode or 1,
            'quality': media_info.quality.value if media_info.quality != QualityLevel.UNKNOWN else "",
            'source': media_info.source or "",
            'codec': media_info.codec or "",
            'audio': media_info.audio or "",
            'language': media_info.language or "",
            'subtitle': media_info.subtitle or "",
            'group': media_info.group or "",
            'extension': media_info.extension.lstrip('.') or "mp4",
            'part_suffix': media_info.part_suffix or "",  # 上中下或特殊版本标识
            'base_episode': media_info.base_episode or media_info.episode or 1  # 原始期数
        }

        # 处理日期相关参数（用于综艺节目）
        if media_info.media_type == MediaType.VARIETY_SHOW:
            # 这里可以根据需要添加日期解析逻辑
            params.update({
                'month': 1,
                'day': 1
            })

            # 处理特殊版本（如纯享版、花絮版等）
            if media_info.base_episode is None and media_info.part_suffix:
                # 特殊版本，使用特殊模板
                params['base_episode'] = ""  # 不显示期数
                # part_suffix 已经在上面设置了

        return params

    def _get_predefined_template(self, template_name: str, media_type: MediaType) -> str:
        """获取预定义模板"""
        # 映射模板名称到实际模板
        template_mapping = {
            # 电视剧模板
            "tv_standard": self.templates,
            "tv_simple": self.simple_templates,
            "tv_chinese": self.chinese_templates,
            "tv_plex": self.templates,  # Plex使用标准模板
            "tv_emby": self.templates,  # Emby使用标准模板

            # 电影模板
            "movie_standard": self.templates,
            "movie_simple": self.simple_templates,
            "movie_chinese": self.chinese_templates,
            "movie_plex": self.templates,
            "movie_emby": self.templates,

            # 综艺模板
            "variety_standard": self.templates,
            "variety_simple": self.simple_templates,
            "variety_chinese": self.chinese_templates,

            # 纪录片模板
            "documentary_standard": self.templates,
            "documentary_simple": self.simple_templates,
            "documentary_chinese": self.chinese_templates,

            # 动漫模板
            "anime_standard": self.templates,
            "anime_simple": self.simple_templates,
            "anime_chinese": self.chinese_templates,

            # 向后兼容的旧风格名称
            "standard": self.templates,
            "simple": self.simple_templates,
            "chinese": self.chinese_templates,
            "plex": self.templates,
            "emby": self.templates,
        }

        template_dict = template_mapping.get(template_name, self.templates)
        return template_dict.get(media_type, template_dict[MediaType.MOVIE])

    def _get_special_variety_template(self, template_name: str) -> str:
        """获取综艺特殊版本模板"""
        if "simple" in template_name:
            return "{title}.{part_suffix}.{extension}"
        elif "chinese" in template_name:
            return "{title} - {part_suffix}.{extension}"
        else:
            return "{title}.{year}{month:02d}{day:02d}.{part_suffix}.{quality}.{extension}"

    def _clean_formatted_name(self, name: str) -> str:
        """清理格式化后的文件名"""
        # 移除多余的点号
        name = re.sub(r'\.{2,}', '.', name)

        # 移除开头和结尾的点号
        name = name.strip('.')

        # 移除空的部分（如 ..mp4 变成 .mp4）
        name = re.sub(r'\.\s*\.', '.', name)

        return name

    def _fallback_format(self, media_info: MediaInfo) -> str:
        """备用格式化方案"""
        title = media_info.title or "Unknown"
        ext = media_info.extension.lstrip('.') or "mp4"

        if media_info.season and media_info.episode:
            return f"{title}.S{media_info.season:02d}E{media_info.episode:02d}.{ext}"
        elif media_info.year:
            return f"{title}.{media_info.year}.{ext}"
        else:
            return f"{title}.{ext}"

class CustomTemplateManager:
    """自定义模板管理器 - 管理用户的自定义重命名模板"""

    def __init__(self):
        self.templates_file = Path(__file__).parent.parent / "config" / "custom_templates.yaml"
        self.templates = {}
        self._load_templates()

        # 预设的常用模板
        self.preset_templates = {
            # 电视剧模板
            "tv_plex": "{title} - S{season:02d}E{episode:02d}.{extension}",
            "tv_emby": "{title}/Season {season:02d}/{title} S{season:02d}E{episode:02d}.{extension}",
            "tv_simple": "{title}.S{season:02d}E{episode:02d}.{extension}",
            "tv_detailed": "{title}.S{season:02d}E{episode:02d}.{year}.{quality}.{source}.{extension}",
            "tv_chinese": "{title}.第{season}季第{episode}集.{extension}",

            # 电影模板
            "movie_imdb": "{title} ({year}).{extension}",
            "movie_detailed": "{title}.{year}.{quality}.{source}.{codec}.{extension}",
            "movie_simple": "{title}.{year}.{extension}",
            "movie_chinese": "{title}.{year}年.{extension}",

            # 综艺节目模板
            "variety_date": "{title}.{year}{month:02d}{day:02d}.第{episode}期.{extension}",
            "variety_simple": "{title}.第{episode}期.{extension}",
            "variety_detailed": "{title}.{year}.第{episode}期.{quality}.{extension}",

            # 动漫模板
            "anime_simple": "{title}.第{episode:02d}话.{extension}",
            "anime_detailed": "{title}.第{episode:02d}话.{quality}.{extension}",

            # 纪录片模板
            "doc_simple": "{title}.{extension}",
            "doc_detailed": "{title}.{year}.{quality}.{source}.{extension}",

            # 特殊格式
            "numbered": "{title}.{episode:03d}.{extension}",
            "date_format": "{title}.{year}-{month:02d}-{day:02d}.{extension}",
            "group_format": "[{group}]{title}.S{season:02d}E{episode:02d}.{extension}"
        }

    def _load_templates(self):
        """加载自定义模板"""
        try:
            if self.templates_file.exists():
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    self.templates = yaml.safe_load(f) or {}
            else:
                self.templates = {}
                self._save_templates()
        except Exception as e:
            logger.error(f"加载自定义模板失败: {e}")
            self.templates = {}

    def _save_templates(self):
        """保存自定义模板"""
        try:
            self.templates_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.templates, f, allow_unicode=True)
        except Exception as e:
            logger.error(f"保存自定义模板失败: {e}")

    def add_template(self, name: str, template: str, description: str = "") -> bool:
        """添加自定义模板"""
        try:
            if self._validate_template(template):
                self.templates[name] = {
                    'template': template,
                    'description': description,
                    'created_at': time.time()
                }
                self._save_templates()
                logger.info(f"添加自定义模板成功: {name}")
                return True
            else:
                logger.error(f"模板验证失败: {template}")
                return False
        except Exception as e:
            logger.error(f"添加自定义模板失败: {e}")
            return False

    def get_template(self, name: str) -> Optional[str]:
        """获取模板"""
        # 先查找自定义模板
        if name in self.templates:
            return self.templates[name]['template']

        # 再查找预设模板
        if name in self.preset_templates:
            return self.preset_templates[name]

        return None

    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模板（包括预设和自定义）"""
        all_templates = {}

        # 添加预设模板
        for name, template in self.preset_templates.items():
            all_templates[name] = {
                'template': template,
                'description': f"预设模板: {name}",
                'type': 'preset'
            }

        # 添加自定义模板
        for name, info in self.templates.items():
            all_templates[name] = {
                'template': info['template'],
                'description': info.get('description', ''),
                'type': 'custom',
                'created_at': info.get('created_at')
            }

        return all_templates

    def remove_template(self, name: str) -> bool:
        """删除自定义模板"""
        try:
            if name in self.templates:
                del self.templates[name]
                self._save_templates()
                logger.info(f"删除自定义模板成功: {name}")
                return True
            else:
                logger.warning(f"模板不存在: {name}")
                return False
        except Exception as e:
            logger.error(f"删除自定义模板失败: {e}")
            return False

    def _validate_template(self, template: str) -> bool:
        """验证模板格式"""
        try:
            # 创建测试参数
            test_params = {
                'title': 'Test Title',
                'season': 1,
                'episode': 1,
                'year': 2023,
                'quality': '1080p',
                'source': 'WEB-DL',
                'codec': 'H264',
                'audio': 'AAC',
                'language': 'chinese',
                'subtitle': '中字',
                'group': 'TestGroup',
                'extension': 'mp4',
                'month': 12,
                'day': 25,
                'episode_title': 'Test Episode'
            }

            # 尝试格式化
            result = template.format(**test_params)

            # 检查结果是否合理
            if len(result) > 255:  # 文件名长度限制
                logger.warning("模板生成的文件名过长")
                return False

            # 检查是否包含非法字符
            illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
            if any(char in result for char in illegal_chars):
                logger.warning("模板生成的文件名包含非法字符")
                return False

            return True
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"模板验证失败: {e}")
            return False

    def preview_template(self, template: str, sample_data: Dict[str, Any] = None) -> str:
        """预览模板效果"""
        try:
            if sample_data is None:
                sample_data = {
                    'title': '示例剧集',
                    'season': 1,
                    'episode': 5,
                    'year': 2023,
                    'quality': '1080p',
                    'source': 'WEB-DL',
                    'codec': 'H264',
                    'extension': 'mp4'
                }

            result = template.format(**sample_data)
            return result
        except Exception as e:
            return f"预览失败: {str(e)}"

    def get_template_variables(self) -> Dict[str, str]:
        """获取可用的模板变量"""
        return {
            'title': '标题 - 媒体文件的主标题',
            'season': '季数 - 电视剧的季数（数字）',
            'episode': '集数 - 集数或期数（数字）',
            'year': '年份 - 发布年份（数字）',
            'quality': '画质 - 如1080p, 720p等',
            'source': '来源 - 如WEB-DL, BluRay等',
            'codec': '编码 - 如H264, H265等',
            'audio': '音频 - 如AAC, DTS等',
            'language': '语言 - 如chinese, english等',
            'subtitle': '字幕 - 如中字, 英字等',
            'group': '发布组 - 发布组名称',
            'extension': '扩展名 - 文件扩展名（不含点）',
            'month': '月份 - 月份（数字，用于综艺节目）',
            'day': '日期 - 日期（数字，用于综艺节目）',
            'episode_title': '集标题 - 单集的标题'
        }

    def add_custom_template(self, name: str, template: str, media_type: MediaType = None) -> bool:
        """添加自定义模板"""
        try:
            # 验证模板
            if self._validate_template(template):
                if media_type:
                    # 为特定媒体类型添加模板
                    if media_type not in self.custom_templates:
                        self.custom_templates[media_type] = {}
                    self.custom_templates[media_type][name] = template
                else:
                    # 添加通用模板
                    self.custom_templates[name] = template
                return True
            else:
                logger.error(f"模板验证失败: {template}")
                return False
        except Exception as e:
            logger.error(f"添加自定义模板失败: {e}")
            return False

    def get_custom_templates(self) -> Dict[str, str]:
        """获取所有自定义模板"""
        return self.custom_templates.copy()

    def remove_custom_template(self, name: str) -> bool:
        """删除自定义模板"""
        try:
            if name in self.custom_templates:
                del self.custom_templates[name]
                return True
            return False
        except Exception as e:
            logger.error(f"删除自定义模板失败: {e}")
            return False

    def _validate_template(self, template: str) -> bool:
        """验证模板格式"""
        try:
            # 创建测试参数
            test_params = {
                'title': 'Test Title',
                'season': 1,
                'episode': 1,
                'year': 2023,
                'quality': '1080p',
                'source': 'WEB-DL',
                'codec': 'H264',
                'audio': 'AAC',
                'language': 'chinese',
                'subtitle': '中字',
                'group': 'TestGroup',
                'extension': 'mp4',
                'month': 12,
                'day': 25,
                'episode_title': 'Test Episode'
            }

            # 尝试格式化
            template.format(**test_params)
            return True
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"模板验证失败: {e}")
            return False

    def get_available_variables(self) -> Dict[str, str]:
        """获取可用的模板变量"""
        return self.get_template_variables()

    def preview_template(self, template: str, sample_data: Dict[str, Any]) -> str:
        """预览模板效果"""
        try:
            formatted_name = template.format(**sample_data)
            return formatted_name
        except Exception as e:
            return f"预览失败: {str(e)}"

class MediaRenamer:
    """媒体重命名器 - 主要的重命名引擎，支持自定义模板"""

    def __init__(self):
        self.analyzer = MediaAnalyzer()
        self.formatter = MediaFormatter()
        self.batch_renamer = SmartBatchRenamer()
        self.template_manager = CustomTemplateManager()
        self.rename_history: List[Dict[str, str]] = []

    def analyze_filename(self, filename: str, context: Dict[str, Any] = None) -> MediaInfo:
        """分析文件名，提取媒体信息（API兼容性方法）"""
        return self.analyzer.analyze(filename, context or {})

    def rename_file(self, filename: str, template_name: str = "standard", custom_title: str = None,
                   custom_template: str = None) -> str:
        """重命名单个文件 - 使用模板"""
        # 分析媒体信息
        context = {'series_title': custom_title} if custom_title else {}
        media_info = self.analyzer.analyze(filename, context)

        # 如果提供了自定义标题，使用自定义标题
        if custom_title:
            media_info.title = custom_title

        # 格式化新文件名
        if custom_template:
            new_filename = self.formatter.format(media_info, template_name=template_name, custom_template=custom_template)
        else:
            # 检查是否为自定义模板名称
            template = self.template_manager.get_template(template_name)
            if template:
                new_filename = self.formatter.format(media_info, template_name=template_name, custom_template=template)
            else:
                # 预设模板
                new_filename = self.formatter.format(media_info, template_name=template_name)

        # 记录重命名历史
        self.rename_history.append({
            'original': filename,
            'renamed': new_filename,
            'media_type': media_info.media_type.value,
            'title': media_info.title
        })

        return new_filename

    def batch_rename(self, filenames: List[str], template_name: str = "standard",
                    custom_title: str = None, directory_path: str = "") -> List[Dict[str, str]]:
        """批量重命名文件 - 使用智能上下文推断"""
        # 使用智能批量重命名器
        results = self.batch_renamer.batch_rename_with_context(
            filenames, directory_path, custom_title
        )

        # 记录到历史
        for result in results:
            if result['status'] == 'success':
                self.rename_history.append({
                    'original': result['original'],
                    'renamed': result['renamed'],
                    'media_type': result.get('media_info', {}).get('media_type', 'unknown'),
                    'title': result.get('media_info', {}).get('title', 'Unknown')
                })

        return results

    def preview_rename(self, filename: str, style: str = "standard",
                      custom_title: str = None) -> Dict[str, Any]:
        """预览重命名结果"""
        context = {'series_title': custom_title} if custom_title else {}
        media_info = self.analyzer.analyze(filename, context)

        if custom_title:
            media_info.title = custom_title

        new_filename = self.formatter.format(media_info, template_name=style)

        return {
            'original': filename,
            'renamed': new_filename,
            'media_info': {
                'title': media_info.title,
                'media_type': media_info.media_type.value,
                'year': media_info.year,
                'season': media_info.season,
                'episode': media_info.episode,
                'quality': media_info.quality.value,
                'source': media_info.source,
                'codec': media_info.codec,
                'base_episode': media_info.base_episode,
                'part_suffix': media_info.part_suffix
            }
        }

    def preview_batch_rename(self, filenames: List[str], directory_path: str = "",
                           custom_title: str = None, style: str = "standard",
                           template_name: str = None) -> Dict[str, Any]:
        """预览批量重命名结果"""
        if template_name:
            template = self.template_manager.get_template(template_name)
            if not template:
                raise ValueError(f"模板不存在: {template_name}")
            return self.batch_renamer.preview_batch_rename_with_template(filenames, template, directory_path, custom_title)
        else:
            return self.batch_renamer.preview_batch_rename(filenames, directory_path, custom_title, None, style)

    def get_rename_history(self) -> List[Dict[str, str]]:
        """获取重命名历史"""
        return self.rename_history.copy()

    def clear_history(self):
        """清空重命名历史"""
        self.rename_history.clear()

    # 自定义模板管理方法
    def add_custom_template(self, name: str, template: str, description: str = "") -> bool:
        """添加自定义模板"""
        return self.template_manager.add_template(name, template, description)

    def get_custom_template(self, name: str) -> Optional[str]:
        """获取自定义模板"""
        return self.template_manager.get_template(name)

    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用模板"""
        return self.template_manager.get_all_templates()

    def remove_custom_template(self, name: str) -> bool:
        """删除自定义模板"""
        return self.template_manager.remove_template(name)

    def preview_template(self, template: str, sample_filename: str = "示例剧集.第01集.mp4") -> str:
        """预览模板效果"""
        try:
            # 分析示例文件
            media_info = self.analyzer.analyze(sample_filename, {'series_title': '示例剧集'})
            return self.template_manager.preview_template(template, {
                'title': media_info.title or '示例剧集',
                'season': media_info.season or 1,
                'episode': media_info.episode or 1,
                'year': 2023,
                'quality': '1080p',
                'source': 'WEB-DL',
                'codec': 'H264',
                'extension': 'mp4'
            })
        except Exception as e:
            return f"预览失败: {str(e)}"

    def get_template_variables(self) -> Dict[str, str]:
        """获取可用的模板变量"""
        return self.template_manager.get_template_variables()

    def start_magic_is_save(self, start_magic: List, filename: str) -> bool:
        """判断文件是否应该保存（基于集数、季数等条件）"""
        try:
            # 分析文件获取媒体信息
            media_info = self.analyzer.analyze(filename)

            for magic_rule in start_magic:
                if not magic_rule:
                    continue

                # 支持字典格式和字符串格式
                if isinstance(magic_rule, dict):
                    # 新的字典格式: {'type': '{E}', 'symbol': '>', 'value': 90}
                    rule_type = magic_rule.get('type', '')
                    symbol = magic_rule.get('symbol', '')
                    value = magic_rule.get('value', 0)

                    # 转换类型标识
                    if rule_type == '{E}' or rule_type == 'episode':
                        field = 'episode'
                    elif rule_type == '{S}' or rule_type == 'season':
                        field = 'season'
                    else:
                        continue

                    # 检查条件
                    if self._check_magic_condition(media_info, field, symbol, value):
                        return True

                elif isinstance(magic_rule, str):
                    # 旧的字符串格式: "episode>90"
                    if self._check_string_magic_rule(media_info, magic_rule):
                        return True

            return False
        except Exception as e:
            logger.warning(f"start_magic_is_save 解析失败: {e}")
            return True  # 默认保存

    def _check_magic_condition(self, media_info, field: str, symbol: str, value: int) -> bool:
        """检查魔法条件"""
        if field == 'episode' and media_info.episode:
            episode = media_info.episode
            if symbol == '>' and episode > value:
                return True
            elif symbol == '>=' and episode >= value:
                return True
            elif symbol == '<' and episode < value:
                return True
            elif symbol == '<=' and episode <= value:
                return True
            elif symbol == '=' and episode == value:
                return True
        elif field == 'season' and media_info.season:
            season = media_info.season
            if symbol == '>' and season > value:
                return True
            elif symbol == '>=' and season >= value:
                return True
            elif symbol == '<' and season < value:
                return True
            elif symbol == '<=' and season <= value:
                return True
            elif symbol == '=' and season == value:
                return True
        return False

    def _check_string_magic_rule(self, media_info, magic_rule: str) -> bool:
        """检查字符串格式的魔法规则"""
        # 解析魔法规则，格式如: "season>=1", "episode<=10", "episode>5"
        if ">=" in magic_rule:
            field, value = magic_rule.split(">=", 1)
            field, value = field.strip(), int(value.strip())
            if field == "season" and media_info.season and media_info.season >= value:
                return True
            elif field == "episode" and media_info.episode and media_info.episode >= value:
                return True
        elif "<=" in magic_rule:
            field, value = magic_rule.split("<=", 1)
            field, value = field.strip(), int(value.strip())
            if field == "season" and media_info.season and media_info.season <= value:
                return True
            elif field == "episode" and media_info.episode and media_info.episode <= value:
                return True
        elif ">" in magic_rule:
            field, value = magic_rule.split(">", 1)
            field, value = field.strip(), int(value.strip())
            if field == "season" and media_info.season and media_info.season > value:
                return True
            elif field == "episode" and media_info.episode and media_info.episode > value:
                return True
        elif "<" in magic_rule:
            field, value = magic_rule.split("<", 1)
            field, value = field.strip(), int(value.strip())
            if field == "season" and media_info.season and media_info.season < value:
                return True
            elif field == "episode" and media_info.episode and media_info.episode < value:
                return True
        elif "=" in magic_rule:
            field, value = magic_rule.split("=", 1)
            field, value = field.strip(), int(value.strip())
            if field == "season" and media_info.season and media_info.season == value:
                return True
            elif field == "episode" and media_info.episode and media_info.episode == value:
                return True

        return False

    def is_exists(self, filename: str, dir_name_list: List[str], ignore_extension: bool = False,
                  check_renamed: bool = True, rename_template: str = "simple", task_name: str = "") -> bool:
        """判断文件是否在目录列表中存在（包括原文件名和重命名后的文件名）"""
        try:
            # 检查原文件名是否存在
            original_exists = self._check_filename_exists(filename, dir_name_list, ignore_extension)

            if not check_renamed:
                return original_exists

            # 如果原文件名已存在，直接返回 True
            if original_exists:
                return True

            # 智能重命名检查：双向检查
            try:
                # 1. 检查新文件重命名后是否与已存在文件匹配
                renamed_filename = self.rename_file(filename, rename_template, task_name)
                logger.debug(f'新文件重命名后: {renamed_filename} {dir_name_list}')
                renamed_exists = self._check_filename_exists(renamed_filename, dir_name_list, ignore_extension)

                if renamed_exists:
                    return True

                # 2. 检查已存在文件重命名后是否与新文件匹配（双向检查）
                return self._check_existing_files_renamed(filename, dir_name_list, rename_template, task_name, ignore_extension)

            except Exception as rename_error:
                logger.warning(f"重命名检查失败: {rename_error}")
                return False

        except Exception as e:
            logger.warning(f"is_exists 检查失败: {e}")
            return False

    def _check_filename_exists(self, filename: str, dir_name_list: List[str], ignore_extension: bool = False) -> bool:
        """检查单个文件名是否在目录列表中存在"""
        if ignore_extension:
            # 忽略扩展名，只比较文件名主体
            filename_base = Path(filename).stem
            for dir_name in dir_name_list:
                dir_name_base = Path(dir_name).stem
                if filename_base.lower() == dir_name_base.lower():
                    return True
        else:
            # 完整文件名比较
            for dir_name in dir_name_list:
                if filename.lower() == dir_name.lower():
                    return True
        return False

    def _check_existing_files_renamed(self, target_filename: str, dir_name_list: List[str],
                                     rename_template: str, task_name: str, ignore_extension: bool = False) -> bool:
        """检查已存在文件重命名后是否与目标文件匹配（双向检查）"""
        try:
            # 分析目标文件的媒体信息
            target_context = {'series_title': task_name} if task_name else {}
            target_media_info = self.analyzer.analyze(target_filename, target_context)

            # 遍历已存在的文件，检查它们重命名后是否与目标文件匹配
            for existing_file in dir_name_list:
                try:
                    # 分析已存在文件的媒体信息
                    existing_context = {'series_title': task_name} if task_name else {}
                    existing_media_info = self.analyzer.analyze(existing_file, existing_context)

                    # 检查是否是同一集内容
                    if self._is_same_episode(target_media_info, existing_media_info):
                        logger.debug(f'找到匹配的已存在文件: {existing_file} <-> {target_filename}')
                        return True

                except Exception as e:
                    logger.debug(f"分析已存在文件失败 {existing_file}: {e}")
                    continue

            # 如果直接比较失败，尝试多种重命名模板进行匹配
            return self._try_multiple_templates_match(target_filename, dir_name_list, task_name, ignore_extension)

        except Exception as e:
            logger.warning(f"双向检查失败: {e}")
            return False

    def _try_multiple_templates_match(self, target_filename: str, dir_name_list: List[str],
                                    task_name: str, ignore_extension: bool = False) -> bool:
        """尝试多种重命名模板进行匹配"""
        try:
            # 常用的重命名模板列表
            common_templates = ['simple', 'standard', 'numbered', 'chinese']

            # 分析目标文件
            target_context = {'series_title': task_name} if task_name else {}
            target_media_info = self.analyzer.analyze(target_filename, target_context)

            if not target_media_info.episode:
                return False

            # 对每个已存在的文件，尝试用不同模板重命名后与目标文件比较
            for existing_file in dir_name_list:
                try:
                    existing_context = {'series_title': task_name} if task_name else {}
                    existing_media_info = self.analyzer.analyze(existing_file, existing_context)

                    if not existing_media_info.episode:
                        continue

                    # 尝试不同的重命名模板
                    for template in common_templates:
                        try:
                            # 将已存在文件用当前模板重命名
                            renamed_existing = self.rename_file(existing_file, template, task_name)
                            # 将目标文件用当前模板重命名
                            renamed_target = self.rename_file(target_filename, template, task_name)

                            # 比较重命名后的文件名
                            if ignore_extension:
                                renamed_existing_base = Path(renamed_existing).stem
                                renamed_target_base = Path(renamed_target).stem
                                if renamed_existing_base.lower() == renamed_target_base.lower():
                                    logger.debug(f'通过模板 {template} 找到匹配: {existing_file} <-> {target_filename}')
                                    return True
                            else:
                                if renamed_existing.lower() == renamed_target.lower():
                                    logger.debug(f'通过模板 {template} 找到匹配: {existing_file} <-> {target_filename}')
                                    return True

                        except Exception as template_error:
                            logger.debug(f"模板 {template} 重命名失败: {template_error}")
                            continue

                except Exception as file_error:
                    logger.debug(f"处理文件 {existing_file} 失败: {file_error}")
                    continue

            return False

        except Exception as e:
            logger.warning(f"多模板匹配失败: {e}")
            return False

    def _is_same_episode(self, media_info1, media_info2) -> bool:
        """判断两个媒体信息是否表示同一集内容"""
        try:
            # 检查标题是否相似（如果都有标题的话）
            if media_info1.title and media_info2.title:
                if media_info1.title.lower() != media_info2.title.lower():
                    return False

            # 检查媒体类型
            if media_info1.media_type != media_info2.media_type:
                return False

            # 检查季数
            if media_info1.season and media_info2.season:
                if media_info1.season != media_info2.season:
                    return False

            # 检查集数（最重要的判断条件）
            if media_info1.episode and media_info2.episode:
                return media_info1.episode == media_info2.episode

            # 如果集数信息不完整，返回 False（保守策略）
            return False

        except Exception as e:
            logger.warning(f"比较媒体信息失败: {e}")
            return False

    def get_episodes(self, filename: str) -> Optional[int]:
        """从文件名中提取集数"""
        try:
            media_info = self.analyzer.analyze(filename)
            return media_info.episode
        except Exception as e:
            logger.warning(f"get_episodes 提取失败: {e}")
            return None

    def get_season(self, filename: str) -> Optional[int]:
        """从文件名中提取季数"""
        try:
            media_info = self.analyzer.analyze(filename)
            return media_info.season
        except Exception as e:
            logger.warning(f"get_season 提取失败: {e}")
            return None

    def process_filename(self, filename: str, template_name: str = "simple", task_name: str = "") -> Any:
        """处理文件名 - 使用模板重命名"""
        class ProcessResult:
            def __init__(self, success: bool, new_name: str):
                self.success = success
                self.new_name = new_name

        try:
            # 使用模板重命名
            if template_name in ['standard', 'simple', 'chinese', 'plex', 'emby']:
                # 预设模板
                new_name = self.rename_file(filename, template_name, task_name)
            else:
                # 自定义模板
                new_name = self.rename_with_template(filename, template_name, task_name)
            return ProcessResult(True, new_name)
        except Exception as e:
            logger.warning(f"process_filename 处理失败: {e}")
            return ProcessResult(False, filename)

    def rename_with_template(self, filename: str, template_name: str, custom_title: str = None) -> str:
        """使用指定模板重命名文件"""
        template = self.template_manager.get_template(template_name)
        if not template:
            raise ValueError(f"模板不存在: {template_name}")

        return self.rename_file(filename, template_name="standard", custom_template=template, custom_title=custom_title)

    def preview_with_template(self, filename: str, template_name: str, custom_title: str = None) -> Dict[str, Any]:
        """使用指定模板预览重命名结果"""
        template = self.template_manager.get_template(template_name)
        if not template:
            raise ValueError(f"模板不存在: {template_name}")

        context = {'series_title': custom_title} if custom_title else {}
        media_info = self.analyzer.analyze(filename, context)

        if custom_title:
            media_info.title = custom_title

        new_filename = self.formatter.format(media_info, custom_template=template)

        return {
            'original': filename,
            'renamed': new_filename,
            'media_info': {
                'title': media_info.title,
                'media_type': media_info.media_type.value,
                'year': media_info.year,
                'season': media_info.season,
                'episode': media_info.episode,
                'quality': media_info.quality.value,
                'source': media_info.source,
                'codec': media_info.codec,
                'base_episode': media_info.base_episode,
                'part_suffix': media_info.part_suffix
            }
        }

# 智能重命名建议器
class SmartRenameSuggester:
    """智能重命名建议器 - 提供多种重命名建议"""

    def __init__(self):
        self.renamer = MediaRenamer()

    def suggest_names(self, filename: str, custom_title: str = None) -> List[Dict[str, str]]:
        """为文件提供多种重命名建议"""
        suggestions = []

        # 标准格式
        standard_result = self.renamer.preview_rename(filename, "standard", custom_title)
        suggestions.append({
            'style': 'standard',
            'name': standard_result['renamed'],
            'description': '标准格式 - 包含完整技术信息'
        })

        # 简洁格式
        simple_result = self.renamer.preview_rename(filename, "simple", custom_title)
        suggestions.append({
            'style': 'simple',
            'name': simple_result['renamed'],
            'description': '简洁格式 - 只包含基本信息'
        })

        # 自定义格式建议
        media_info = self.renamer.analyzer.analyze(filename)
        if custom_title:
            media_info.title = custom_title

        # 根据媒体类型提供特定建议
        if media_info.media_type == MediaType.TV_SERIES:
            suggestions.extend(self._suggest_tv_formats(media_info))
        elif media_info.media_type == MediaType.MOVIE:
            suggestions.extend(self._suggest_movie_formats(media_info))

        return suggestions

    def _suggest_tv_formats(self, media_info: MediaInfo) -> List[Dict[str, str]]:
        """为电视剧提供特定格式建议"""
        suggestions = []

        # Plex格式
        if media_info.season and media_info.episode:
            plex_name = f"{media_info.title} - S{media_info.season:02d}E{media_info.episode:02d}.{media_info.extension.lstrip('.')}"
            suggestions.append({
                'style': 'plex',
                'name': plex_name,
                'description': 'Plex媒体服务器格式'
            })

        # Emby格式
        if media_info.season and media_info.episode:
            emby_name = f"{media_info.title}/Season {media_info.season:02d}/{media_info.title} S{media_info.season:02d}E{media_info.episode:02d}.{media_info.extension.lstrip('.')}"
            suggestions.append({
                'style': 'emby',
                'name': emby_name,
                'description': 'Emby媒体服务器格式'
            })

        return suggestions

    def _suggest_movie_formats(self, media_info: MediaInfo) -> List[Dict[str, str]]:
        """为电影提供特定格式建议"""
        suggestions = []

        # IMDb格式
        if media_info.year:
            imdb_name = f"{media_info.title} ({media_info.year}).{media_info.extension.lstrip('.')}"
            suggestions.append({
                'style': 'imdb',
                'name': imdb_name,
                'description': 'IMDb标准格式'
            })

        return suggestions

# 创建全局实例，保持向后兼容
media_renamer = MediaRenamer()
smart_suggester = SmartRenameSuggester()

# 兼容性包装器
class SmartRenameEngine:
    """向后兼容的包装器"""

    def __init__(self, custom_patterns=None):
        self.renamer = MediaRenamer()
        self.task_name = ""

    def set_task_name(self, name: str):
        """设置任务名称"""
        self.task_name = name

    def transform_filename(self, pattern: str, replacement: str, filename: str) -> str:
        """转换文件名 - 兼容旧API"""
        return self.renamer.rename_file(filename, template_name="simple", custom_title=self.task_name)

    def apply_text_pattern(self, pattern_key: str, replacement: str, filename: str) -> Tuple[str, str]:
        """应用文本模式 - 兼容旧API"""
        return pattern_key, replacement


