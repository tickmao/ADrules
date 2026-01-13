#!/usr/bin/env python3
"""
ADrules 自动更新脚本
自动从源站拉取最新的广告过滤规则
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional
import requests
import yaml


class RuleUpdater:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.root_dir = Path(__file__).parent.parent
        self.updated_count = 0
        self.skipped_count = 0
        self.failed_count = 0

    def _load_config(self) -> dict:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _parse_metadata(self, content: str) -> Dict[str, str]:
        """从规则内容中提取元数据"""
        metadata = {}
        lines = content.split('\n')[:30]  # 只检查前30行

        for line in lines:
            if line.startswith('!') or line.startswith('#'):
                # 提取 Version
                if 'Version:' in line or 'version:' in line:
                    match = re.search(r'[Vv]ersion:\s*(.+)', line)
                    if match:
                        metadata['version'] = match.group(1).strip()

                # 提取 Title
                if 'Title:' in line or 'title:' in line:
                    match = re.search(r'[Tt]itle:\s*(.+)', line)
                    if match:
                        metadata['title'] = match.group(1).strip()

                # 提取 Last modified
                if 'Last modified:' in line or 'Last Modified:' in line:
                    match = re.search(r'[Ll]ast [Mm]odified:\s*(.+)', line)
                    if match:
                        metadata['last_modified'] = match.group(1).strip()

        return metadata

    def _get_current_version(self, filename: str) -> Optional[str]:
        """获取当前文件的版本号"""
        filepath = self.root_dir / filename
        if not filepath.exists():
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(5000)  # 只读取前5000字符
                metadata = self._parse_metadata(content)
                return metadata.get('version')
        except Exception as e:
            print(f"  ⚠️  读取当前版本失败: {e}")
            return None

    def _validate_content(self, content: str, rule_config: dict) -> bool:
        """验证规则内容的有效性"""
        strategy = self.config['update_strategy']

        # 检查最小行数
        lines = content.split('\n')
        if len(lines) < strategy['min_lines']:
            print(f"  ✗ 行数过少: {len(lines)} < {strategy['min_lines']}")
            return False

        # 检查文件大小
        size_mb = len(content.encode('utf-8')) / (1024 * 1024)
        if size_mb > strategy['max_size_mb']:
            print(f"  ✗ 文件过大: {size_mb:.2f}MB > {strategy['max_size_mb']}MB")
            return False

        # 检查基本格式（至少包含一些规则标记）
        has_rules = any(marker in content for marker in ['||', '@@||', '##', '#@#', '!'])
        if not has_rules:
            print(f"  ✗ 未检测到有效的规则格式")
            return False

        return True

    def _download_rule(self, url: str) -> Optional[str]:
        """下载规则文件"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"  ✗ 下载失败: {e}")
            return None

    def _save_rule(self, content: str, filename: str):
        """保存规则文件"""
        filepath = self.root_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    def update_rule(self, rule_config: dict) -> str:
        """更新单个规则"""
        name = rule_config['name']
        url = rule_config['url']
        filename = rule_config['filename']

        print(f"\n→ {name}")
        print(f"  URL: {url}")

        # 下载规则
        content = self._download_rule(url)
        if not content:
            return 'failed'

        # 提取元数据
        metadata = self._parse_metadata(content)
        new_version = metadata.get('version', 'unknown')
        print(f"  版本: {new_version}")

        # 版本比对
        if self.config['update_strategy']['check_version']:
            current_version = self._get_current_version(filename)
            if current_version and current_version == new_version:
                print(f"  ✓ 版本相同，跳过更新")
                return 'skipped'

        # 格式验证
        if self.config['update_strategy']['verify_format']:
            if not self._validate_content(content, rule_config):
                return 'failed'

        # 保存文件
        try:
            self._save_rule(content, filename)
            lines = len(content.split('\n'))
            size_kb = len(content.encode('utf-8')) / 1024
            print(f"  ✓ 更新成功 ({lines} 行, {size_kb:.1f}KB)")
            return 'updated'
        except Exception as e:
            print(f"  ✗ 保存失败: {e}")
            return 'failed'

    def run(self):
        """执行更新"""
        print("=" * 60)
        print("ADrules 自动更新")
        print("=" * 60)

        rules = self.config['rules']
        total = len(rules)

        for i, rule in enumerate(rules, 1):
            print(f"\n[{i}/{total}] 处理规则...")
            result = self.update_rule(rule)

            if result == 'updated':
                self.updated_count += 1
            elif result == 'skipped':
                self.skipped_count += 1
            elif result == 'failed':
                self.failed_count += 1

        # 输出统计
        print("\n" + "=" * 60)
        print("更新完成")
        print("=" * 60)
        print(f"✓ 更新: {self.updated_count}")
        print(f"→ 跳过: {self.skipped_count}")
        print(f"✗ 失败: {self.failed_count}")
        print(f"总计: {total}")

        # 如果有失败的，返回非零退出码
        if self.failed_count > 0:
            sys.exit(1)


def main():
    config_path = Path(__file__).parent / 'config.yaml'
    updater = RuleUpdater(str(config_path))
    updater.run()


if __name__ == '__main__':
    main()
