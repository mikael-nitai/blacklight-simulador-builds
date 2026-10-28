"""Audit output must not omit changed project Python sources."""

from pathlib import Path
import tempfile
import unittest

from scripts.audit_manifest import audit_source_manifest, require_audit_sources_unchanged


class TestAuditManifest(unittest.TestCase):
    def test_source_changes_and_new_files_abort_the_audit(self):
        with tempfile.TemporaryDirectory(prefix='blacklight-audit-manifest-') as temporary:
            root = Path(temporary).resolve()
            if (not root.is_relative_to(Path(tempfile.gettempdir()).resolve())
                    or not root.name.startswith('blacklight-audit-manifest-')):
                raise AssertionError('Unexpected temporary fixture path')
            (root / 'blacklight').mkdir()
            source = root / 'blacklight' / 'core.py'
            source.write_text('before', encoding='utf-8')
            before = audit_source_manifest(root)
            self.assertEqual(list(before), ['blacklight/core.py'])
            require_audit_sources_unchanged(before, root)
            source.write_text('after', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'sources changed'):
                require_audit_sources_unchanged(before, root)
            source.write_text('before', encoding='utf-8')
            (root / 'blacklight' / 'new.py').write_text('new', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'sources changed'):
                require_audit_sources_unchanged(before, root)


if __name__ == '__main__':
    unittest.main()
