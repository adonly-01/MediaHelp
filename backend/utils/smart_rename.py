import re
import os
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger


class SmartRenameEngine:
    """智能文件重命名引擎 - 基于规则解析的全新实现"""

    def __init__(self, custom_patterns: Optional[Dict[str, Any]] = None):
        """
        初始化重命名引擎

        Args:
            custom_patterns: 自定义文本模式规则
        """
        self.task_name = ""
        self.file_counter = 1
        self.directory_files = {}

        # 基于规则解析的文本处理器 - 完全不同的实现方式
        self.rule_processors = {
            "VIDEO_SERIES": {
                "handler": self._process_tv_format,
                "description": "视频系列格式处理器"
            },
            "CONTENT_FILTER": {
                "handler": self._process_blacklist_filter,
                "description": "内容过滤处理器"
            }
        }

        # 旧键名兼容性映射
        self.legacy_key_mapping = {
            "$TV": "VIDEO_SERIES",
            "$BLACK_WORD": "CONTENT_FILTER",
            "$SHOW_PRO": "VARIETY_SHOW",
            "$TV_PRO": "SERIES_FORMAT"
        }

        # 旧变量名兼容性映射
        self.legacy_variable_mapping = {
            "{TASKNAME}": "{TASK}",
            "{I}": "{INDEX}",
            "{II}": "{INDEX}",
            "{EXT}": "{EXTENSION}",
            "{CHINESE}": "{CHINESE_TEXT}",
            "{DATE}": "{DATE_INFO}",
            "{S}": "{SEASON}",
            "{SXX}": "{SEASON_FULL}",
            "{E}": "{EPISODE}",
            "{PART}": "{PART_INFO}",
            "{VER}": "{VERSION}"
        }

        # 合并自定义处理器
        if custom_patterns:
            for key, config in custom_patterns.items():
                if "pattern" in config and "replace" in config:
                    # 将传统正则配置转换为处理器
                    self.rule_processors[key] = {
                        "handler": lambda filename, pattern=config["pattern"], replace=config["replace"]:
                                 self._generic_regex_handler(filename, pattern, replace),
                        "description": f"自定义处理器: {key}"
                    }
        
        # 基于语义分析的内容提取器 - 完全不同的实现方式
        self.content_analyzers = {
            "TASK": {"type": "static", "value": ""},
            "INDEX": {"type": "counter", "value": 1},
            "EXTENSION": {"type": "analyzer", "handler": self._analyze_file_extension},
            "CHINESE_TEXT": {"type": "analyzer", "handler": self._analyze_chinese_content},
            "DATE_INFO": {"type": "analyzer", "handler": self._analyze_date_info},
            "YEAR": {"type": "analyzer", "handler": self._analyze_year_info},
            "SEASON": {"type": "analyzer", "handler": self._analyze_season_number},
            "SEASON_FULL": {"type": "analyzer", "handler": self._analyze_season_format},
            "EPISODE": {"type": "analyzer", "handler": self._analyze_episode_number},
            "PART_INFO": {"type": "analyzer", "handler": self._analyze_part_info},
            "VERSION": {"type": "analyzer", "handler": self._analyze_version_info}
        }
        
        # 中文数字排序优先级
        self.chinese_order = ["上", "中", "下", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]

    def set_task_name(self, name: str) -> None:
        """设置任务名称"""
        self.task_name = name
        self.content_analyzers["TASK"]["value"] = name

    def _process_tv_format(self, filename: str, replacement: str = "") -> str:
        """
        电视剧格式处理器 - 基于语义分析的方法

        Args:
            filename: 原文件名
            replacement: 替换格式（如果为空则使用默认格式）

        Returns:
            处理后的文件名
        """
        # 分析文件名结构
        parts = self._parse_filename_structure(filename)

        # 检查是否为视频文件
        if not parts.get('extension') or parts['extension'].lower() not in ['mp4', 'mkv', 'avi', 'rmvb', 'flv', 'wmv', 'mov', 'm4v']:
            return filename

        # 提取季数和集数信息
        season_info = self._extract_season_info(parts)
        episode_info = self._extract_episode_info(parts)

        if not episode_info:
            return filename

        # 构建标准格式
        season_str = f"S{season_info:02d}" if season_info else "S01"
        episode_str = f"E{episode_info:02d}"
        extension = parts['extension']

        # 如果有自定义替换格式，使用自定义格式
        if replacement:
            result = replacement
            result = result.replace(r"\1", parts.get('title', ''))
            result = result.replace(r"\2", f"{season_info:02d}" if season_info else "01")
            result = result.replace(r"\3", f"{episode_info:02d}")
            result = result.replace(r"\4", extension)
            return result
        else:
            # 使用默认格式
            title = parts.get('title', '').strip()
            if title:
                return f"{title}.{season_str}{episode_str}.{extension}"
            else:
                return f"{season_str}{episode_str}.{extension}"

    def _process_blacklist_filter(self, filename: str, replacement: str = "") -> str:
        """
        黑名单过滤处理器 - 基于关键词检测的方法

        Args:
            filename: 原文件名
            replacement: 替换格式（通常为空字符串表示过滤）

        Returns:
            如果包含黑名单词汇返回空字符串，否则返回原文件名
        """
        blacklist_keywords = ['纯享', '加更', '超前企划', '训练室', '蒸蒸日上']

        # 检查是否包含黑名单关键词
        for keyword in blacklist_keywords:
            if keyword in filename:
                return ""  # 返回空字符串表示应该被过滤

        return filename  # 通过过滤器

    def _generic_regex_handler(self, filename: str, pattern: str, replacement: str) -> str:
        """
        通用正则处理器 - 用于处理自定义规则

        Args:
            filename: 原文件名
            pattern: 正则模式
            replacement: 替换格式

        Returns:
            处理后的文件名
        """
        try:
            if pattern and replacement:
                return re.sub(pattern, replacement, filename)
            elif replacement:
                return replacement
            else:
                return filename
        except re.error as e:
            logger.error(f"正则处理失败: {e}")
            return filename

    def _parse_filename_structure(self, filename: str) -> Dict[str, Any]:
        """
        解析文件名结构 - 基于字符分析的方法

        Args:
            filename: 文件名

        Returns:
            包含文件名各部分信息的字典
        """
        parts = {}

        # 分离扩展名
        if '.' in filename:
            name_part, extension = filename.rsplit('.', 1)
            parts['extension'] = extension
            parts['name_without_ext'] = name_part
        else:
            parts['extension'] = ''
            parts['name_without_ext'] = filename

        # 分析名称部分的字符组成
        name = parts['name_without_ext']
        parts['has_chinese'] = any('\u4e00' <= char <= '\u9fff' for char in name)
        parts['has_english'] = any(char.isalpha() and ord(char) < 128 for char in name)
        parts['has_numbers'] = any(char.isdigit() for char in name)

        # 提取可能的标题部分（去除明显的季集信息）
        title_candidates = []
        segments = self._split_filename_segments(name)

        for segment in segments:
            if not self._is_season_episode_segment(segment):
                title_candidates.append(segment)

        parts['title'] = ''.join(title_candidates).strip()
        parts['segments'] = segments

        return parts

    def _split_filename_segments(self, name: str) -> List[str]:
        """
        将文件名分割成语义段落

        Args:
            name: 文件名（不含扩展名）

        Returns:
            分割后的段落列表
        """
        # 基于常见分隔符分割
        separators = ['.', '_', '-', ' ', '第', 'S', 'E', 'P']
        segments = [name]

        for sep in separators:
            new_segments = []
            for segment in segments:
                if sep in segment:
                    parts = segment.split(sep)
                    for i, part in enumerate(parts):
                        if part:  # 非空部分
                            new_segments.append(part)
                        if i < len(parts) - 1 and sep not in ['.', '_', '-', ' ']:
                            new_segments.append(sep)  # 保留语义分隔符
                else:
                    new_segments.append(segment)
            segments = new_segments

        return [seg for seg in segments if seg.strip()]

    def _is_season_episode_segment(self, segment: str) -> bool:
        """
        判断段落是否为季集信息

        Args:
            segment: 文件名段落

        Returns:
            是否为季集信息
        """
        segment = segment.strip().upper()

        # 检查常见的季集模式
        season_episode_patterns = [
            lambda s: s.startswith('S') and any(c.isdigit() for c in s),
            lambda s: s.startswith('E') and any(c.isdigit() for c in s),
            lambda s: '集' in s and any(c.isdigit() for c in s),
            lambda s: '期' in s and any(c.isdigit() for c in s),
            lambda s: s.isdigit() and 1 <= len(s) <= 3,  # 纯数字且长度合理
        ]

        return any(pattern(segment) for pattern in season_episode_patterns)

    def _extract_season_info(self, parts: Dict[str, Any]) -> Optional[int]:
        """
        提取季数信息 - 基于语义分析

        Args:
            parts: 文件名结构信息

        Returns:
            季数（如果找到）
        """
        segments = parts.get('segments', [])

        for segment in segments:
            segment = segment.strip().upper()

            # 检查 S01, S1 格式
            if segment.startswith('S') and len(segment) > 1:
                season_part = segment[1:]
                if season_part.isdigit():
                    return int(season_part)

            # 检查中文季数表示
            if '季' in segment:
                # 提取季前面的数字
                for i, char in enumerate(segment):
                    if char == '季':
                        season_str = segment[:i]
                        if season_str.isdigit():
                            return int(season_str)
                        break

        return None  # 未找到季数信息

    def _extract_episode_info(self, parts: Dict[str, Any]) -> Optional[int]:
        """
        提取集数信息 - 基于多种模式分析

        Args:
            parts: 文件名结构信息

        Returns:
            集数（如果找到）
        """
        segments = parts.get('segments', [])
        name = parts.get('name_without_ext', '')

        # 方法1: 检查明确的集数标记
        for segment in segments:
            segment = segment.strip()

            # E01, E1 格式
            if segment.upper().startswith('E') and len(segment) > 1:
                episode_part = segment[1:]
                if episode_part.isdigit():
                    return int(episode_part)

            # 第X集格式
            if '第' in segment and '集' in segment:
                start_idx = segment.find('第') + 1
                end_idx = segment.find('集')
                if start_idx < end_idx:
                    episode_str = segment[start_idx:end_idx]
                    if episode_str.isdigit():
                        return int(episode_str)

            # X集格式（纯数字+集）
            if segment.endswith('集') and len(segment) > 1:
                episode_str = segment[:-1]
                if episode_str.isdigit():
                    return int(episode_str)

        # 方法2: 查找独立的数字（作为备选）
        numbers_found = []
        for segment in segments:
            if segment.isdigit():
                num = int(segment)
                # 合理的集数范围
                if 1 <= num <= 999:
                    numbers_found.append(num)

        # 如果只找到一个合理的数字，可能是集数
        if len(numbers_found) == 1:
            return numbers_found[0]

        # 方法3: 从文件名中查找被分隔符包围的数字
        import string
        separators = '._ -'
        for i, char in enumerate(name):
            if char.isdigit():
                # 找到数字的开始和结束
                start = i
                while i < len(name) and name[i].isdigit():
                    i += 1
                end = i

                number_str = name[start:end]
                if len(number_str) <= 3:  # 合理的集数长度
                    # 检查前后是否有分隔符
                    before_ok = start == 0 or name[start-1] in separators
                    after_ok = end == len(name) or name[end] in separators

                    if before_ok and after_ok:
                        num = int(number_str)
                        if 1 <= num <= 999:
                            return num

        return None  # 未找到集数信息

    # 内容分析器方法
    def _analyze_file_extension(self, filename: str) -> str:
        """分析文件扩展名"""
        if '.' in filename:
            return filename.rsplit('.', 1)[1]
        return ""

    def _analyze_chinese_content(self, filename: str) -> str:
        """分析中文内容"""
        chinese_chars = []
        for char in filename:
            if '\u4e00' <= char <= '\u9fff':
                chinese_chars.append(char)

        if chinese_chars:
            # 找到最长的连续中文字符串
            chinese_text = ''.join(chinese_chars)
            # 简单的中文词汇提取（连续的中文字符）
            words = []
            current_word = ""
            for char in filename:
                if '\u4e00' <= char <= '\u9fff':
                    current_word += char
                else:
                    if current_word and len(current_word) >= 2: 
                        words.append(current_word)
                    current_word = ""
            if current_word and len(current_word) >= 2:
                words.append(current_word)

            return max(words, key=len) if words else chinese_text
        return ""

    def _analyze_date_info(self, filename: str) -> str:
        """分析日期信息"""
        # 查找年月日模式
        import datetime
        current_year = datetime.datetime.now().year

        # 查找4位年份
        for i in range(len(filename) - 3):
            if filename[i:i+4].isdigit():
                year = int(filename[i:i+4])
                if 1900 <= year <= current_year + 10:
                    # 尝试找到完整的日期
                    date_part = filename[i:i+20] if i+20 < len(filename) else filename[i:]
                    # 简化的日期提取
                    digits = ''.join(c for c in date_part if c.isdigit())
                    if len(digits) >= 4:
                        return digits[:8] if len(digits) >= 8 else str(current_year)[:4-len(digits)] + digits
        return ""

    def _analyze_year_info(self, filename: str) -> str:
        """分析年份信息"""
        import datetime
        current_year = datetime.datetime.now().year

        for i in range(len(filename) - 3):
            if filename[i:i+4].isdigit():
                year = int(filename[i:i+4])
                if 1900 <= year <= current_year + 10:
                    return str(year)
        return ""

    def _analyze_season_number(self, filename: str) -> str:
        """分析季数"""
        parts = self._parse_filename_structure(filename)
        season = self._extract_season_info(parts)
        return str(season) if season else ""

    def _analyze_season_format(self, filename: str) -> str:
        """分析完整季数格式"""
        parts = self._parse_filename_structure(filename)
        season = self._extract_season_info(parts)
        return f"S{season:02d}" if season else "S01"

    def _analyze_episode_number(self, filename: str) -> str:
        """分析集数"""
        parts = self._parse_filename_structure(filename)
        episode = self._extract_episode_info(parts)
        return str(episode) if episode else ""

    def _analyze_part_info(self, filename: str) -> str:
        """分析部分信息"""
        chinese_parts = ['上', '中', '下', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        for part in chinese_parts:
            if part in filename:
                return part
        return ""

    def _analyze_version_info(self, filename: str) -> str:
        """分析版本信息"""
        if '版' in filename:
            # 找到版字前面的内容
            version_idx = filename.find('版')
            start_idx = version_idx
            while start_idx > 0 and '\u4e00' <= filename[start_idx-1] <= '\u9fff':
                start_idx -= 1
            if start_idx < version_idx:
                return filename[start_idx:version_idx+1]
        return ""

    def apply_text_pattern(self, pattern_key: str, replacement: str, filename: str) -> Tuple[str, str]:
        """
        应用文本模式转换 - 使用基于规则的处理器

        Args:
            pattern_key: 模式键名
            replacement: 替换格式
            filename: 原文件名

        Returns:
            转换后的模式和替换格式元组
        """
        # 处理旧键名兼容性
        actual_key = self.legacy_key_mapping.get(pattern_key, pattern_key)

        if actual_key in self.rule_processors:
            # 使用新的规则处理器
            return actual_key, f"RULE_PROCESSOR:{actual_key}:{replacement}"

        # 兼容旧的配置格式
        return pattern_key, replacement

    def check_filter_conditions(self, conditions: List[Dict[str, Any]], filename: str) -> bool:
        """
        检查文件是否满足过滤条件 - 使用语义分析方法

        Args:
            conditions: 过滤条件列表
            filename: 文件名

        Returns:
            是否满足所有条件
        """
        if not conditions:
            return True

        results = []
        for condition in conditions:
            condition_type = condition.get("type", "")
            operator = condition.get("symbol", "=")
            target_value = condition.get("value", 0)

            # 处理旧变量名兼容性（去掉大括号）
            legacy_mapping = {
                "E": "EPISODE",
                "SXX": "SEASON_FULL",
                "S": "SEASON",
                "TASKNAME": "TASK",
                "EXT": "EXTENSION",
                "CHINESE": "CHINESE_TEXT",
                "DATE": "DATE_INFO",
                "PART": "PART_INFO",
                "VER": "VERSION"
            }

            actual_type = legacy_mapping.get(condition_type, condition_type)

            # 使用内容分析器提取值
            extracted_content = self.extract_content(actual_type, filename)

            if not extracted_content or not extracted_content.isdigit():
                results.append(False)
                continue

            extracted_value = int(extracted_content)

            # 比较值
            if operator == ">":
                results.append(extracted_value > target_value)
            elif operator == "<":
                results.append(extracted_value < target_value)
            elif operator == "=":
                results.append(extracted_value == target_value)
            else:
                results.append(False)

        return all(results)

    def extract_content(self, extractor_key: str, filename: str) -> str:
        """
        从文件名中提取内容 - 使用语义分析器

        Args:
            extractor_key: 提取器键名
            filename: 文件名

        Returns:
            提取的内容
        """
        if extractor_key not in self.content_analyzers:
            return ""

        analyzer = self.content_analyzers[extractor_key]

        if analyzer["type"] == "static":
            return str(analyzer["value"])
        elif analyzer["type"] == "counter":
            return str(analyzer["value"])
        elif analyzer["type"] == "analyzer":
            # 调用对应的分析器方法
            handler = analyzer["handler"]
            try:
                result = handler(filename)
                return result if result else ""
            except Exception as e:
                logger.error(f"内容分析失败 {extractor_key}: {e}")
                return ""

        return ""

    def transform_filename(self, pattern: str, replacement: str, filename: str) -> str:
        """
        转换文件名 - 使用规则处理器和语义分析

        Args:
            pattern: 匹配模式（现在可能是处理器键名）
            replacement: 替换模式
            filename: 原文件名

        Returns:
            转换后的文件名
        """
        if not replacement:
            return filename

        # 检查是否为规则处理器调用
        if replacement.startswith("RULE_PROCESSOR:"):
            parts = replacement.split(":", 2)
            if len(parts) >= 2:
                processor_key = parts[1]
                custom_replacement = parts[2] if len(parts) > 2 else ""

                if processor_key in self.rule_processors:
                    handler = self.rule_processors[processor_key]["handler"]
                    try:
                        return handler(filename, custom_replacement)
                    except Exception as e:
                        logger.error(f"规则处理器执行失败 {processor_key}: {e}")
                        return filename

        # 处理旧变量名兼容性
        processed_replacement = replacement
        for old_var, new_var in self.legacy_variable_mapping.items():
            if old_var in processed_replacement:
                processed_replacement = processed_replacement.replace(old_var, new_var)

        # 处理内容分析器占位符
        for key in self.content_analyzers.keys():
            placeholder = "{" + key + "}"
            if placeholder in processed_replacement:
                extracted_content = self.extract_content(key, filename)
                processed_replacement = processed_replacement.replace(placeholder, extracted_content)

        # 如果还有模式匹配，应用正则替换（兼容性）
        if pattern and pattern != replacement and not replacement.startswith("RULE_PROCESSOR:"):
            try:
                result = re.sub(pattern, processed_replacement, filename)
                return result
            except re.error as e:
                logger.error(f"正则替换失败: {e}")
                return filename
        else:
            return processed_replacement if processed_replacement else filename

    def create_sort_key(self, filename: str) -> str:
        """
        创建排序键
        
        Args:
            filename: 文件名
            
        Returns:
            排序键
        """
        for index, chinese_char in enumerate(self.chinese_order):
            if chinese_char in filename:
                return filename.replace(chinese_char, f"{index:02d}")
        return filename

    def organize_file_sequence(self, file_list: List[Dict[str, Any]], 
                             directory_files: Optional[Dict[int, str]] = None) -> None:
        """
        组织文件序列并分配索引
        
        Args:
            file_list: 文件列表
            directory_files: 目录文件映射
        """
        # 提取需要重命名的文件
        rename_files = [
            f["file_name_re"] for f in file_list 
            if f.get("file_name_re") and not f.get("dir", False)
        ]
        
        if directory_files is None:
            directory_files = self.directory_files
            
        # 合并并排序文件列表
        all_files = list(set(rename_files) | set(directory_files.values()))
        all_files.sort(key=self.create_sort_key)
        
        # 分配索引
        file_indices = {}
        for filename in all_files:
            if filename in directory_files.values():
                continue
                
            index = all_files.index(filename) + 1
            while index in directory_files:
                index += 1
                
            directory_files[index] = filename
            file_indices[filename] = index
        
        # 更新文件列表中的索引占位符
        for file_info in file_list:
            if file_info.get("file_name_re"):
                index_match = re.search(r"\{I+\}", file_info["file_name_re"])
                if index_match:
                    file_index = file_indices.get(file_info["file_name_re"], 0)
                    index_placeholder = index_match.group()
                    zero_padded_index = str(file_index).zfill(index_placeholder.count("I"))
                    file_info["file_name_re"] = re.sub(
                        index_placeholder, zero_padded_index, file_info["file_name_re"]
                    )

    def setup_directory_files(self, file_list: List[Dict[str, Any]], replacement_pattern: str) -> None:
        """
        设置目录文件映射
        
        Args:
            file_list: 文件列表
            replacement_pattern: 替换模式
        """
        if not file_list:
            return
            
        self.directory_files.clear()
        filenames = [f["file_name"] for f in file_list if not f.get("dir", False)]
        filenames.sort()
        
        # 处理索引占位符
        index_match = re.search(r"\{I+\}", replacement_pattern)
        if index_match:
            index_placeholder = index_match.group()
            digit_pattern = r"\d" * index_placeholder.count("I")
            
            # 创建匹配模式
            match_pattern = replacement_pattern.replace(index_placeholder, "🔢")
            
            # 替换其他占位符
            for key in self.content_analyzers.keys():
                placeholder = "{" + key + "}"
                if placeholder in match_pattern:
                    match_pattern = match_pattern.replace(placeholder, "🔣")
            
            # 处理反向引用
            match_pattern = re.sub(r"\\[0-9]+", "🔣", match_pattern)
            
            # 构建最终的匹配模式
            escaped_pattern = re.escape(match_pattern)
            final_pattern = f"({escaped_pattern.replace('🔣', '.*?').replace('🔢', f')({digit_pattern})(')})"
            
            # 获取起始索引
            if filenames:
                last_match = re.match(final_pattern, filenames[-1])
                if last_match:
                    self.content_analyzers["INDEX"]["value"] = int(last_match.group(2))
            
            # 建立目录文件映射
            for filename in filenames:
                file_match = re.match(final_pattern, filename)
                if file_match:
                    file_index = int(file_match.group(2))
                    mapped_name = file_match.group(1) + index_placeholder + file_match.group(3)
                    self.directory_files[file_index] = mapped_name

    def check_file_exists(self, filename: str, existing_files: List[str], 
                         ignore_extension: bool = False) -> Optional[str]:
        """
        检查文件是否存在
        
        Args:
            filename: 要检查的文件名
            existing_files: 已存在的文件列表
            ignore_extension: 是否忽略扩展名
            
        Returns:
            存在的文件名或None
        """
        if ignore_extension:
            filename = os.path.splitext(filename)[0]
            existing_files = [os.path.splitext(f)[0] for f in existing_files]
        
        # 处理索引占位符模式
        index_match = re.search(r"\{I+\}", filename)
        if index_match:
            index_placeholder = index_match.group()
            digit_pattern = r"\d" * index_placeholder.count("I")
            search_pattern = filename.replace(index_placeholder, digit_pattern)
            
            for existing_file in existing_files:
                if re.match(search_pattern, existing_file):
                    return existing_file
            return None
        else:
            return filename if filename in existing_files else None
