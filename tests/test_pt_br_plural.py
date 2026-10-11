import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import lt_server
import plurale_pt_br


class LocalTranslatorTests(unittest.TestCase):
    def test_uses_local_model_and_decodes_batch(self):
        class FakeModel:
            def __init__(self, model_path, **kwargs):
                self.model_path = model_path
                self.kwargs = kwargs

            def translate_batch(self, tokenized, **kwargs):
                self.tokenized = tokenized
                self.options = kwargs
                return [
                    types.SimpleNamespace(hypotheses=[["▁Olá", "▁mundo", "."]]),
                    types.SimpleNamespace(hypotheses=[["▁Bem", "-", "vindos", "."]]),
                ]

        class FakeSentencePiece:
            def __init__(self, model_file):
                self.model_file = model_file

            def encode(self, text, out_type):
                return [text, out_type]

            def decode_pieces(self, pieces):
                return "".join(pieces)

        fake_ct2 = types.ModuleType("ctranslate2")
        fake_ct2.Translator = FakeModel
        fake_spm = types.ModuleType("sentencepiece")
        fake_spm.SentencePieceProcessor = FakeSentencePiece
        with tempfile.TemporaryDirectory() as temp:
            package_dir = Path(temp)
            (package_dir / "model").mkdir()
            (package_dir / "model" / "model.bin").touch()
            (package_dir / "sentencepiece.model").touch()
            with patch.dict(sys.modules, {"ctranslate2": fake_ct2, "sentencepiece": fake_spm}):
                translator = lt_server.CT2Translator(package_dir, threads=2)
            self.assertEqual(translator.translate(["Hello world", "Welcome"]),
                             ["Olá mundo.", "Bem-vindos."])
            self.assertEqual(translator.tr.kwargs["intra_threads"], 2)
            self.assertEqual(translator.sp.model_file, str(package_dir / "sentencepiece.model"))
            self.assertEqual(translator.tr.options["beam_size"], 2)

    def test_engine_restores_game_tokens_and_glossary_terms(self):
        class PlaceholderTranslator:
            def translate(self, _texts):
                return ["Fale com QZ0QZ em QZ1QZ"]

        glossary = lt_server.Glossary()
        glossary.load_file(Path(__file__).resolve().parents[1] / "src" / "glossary_pt-br.default.json")
        engine = lt_server.Engine(PlaceholderTranslator(), glossary)
        result = engine._translate_plain(["Talk to %str1% at Lion's Arch"])
        self.assertEqual(result["Talk to %str1% at Lion's Arch"],
                         "Fale com %str1% em Arco do Leão")


class PortuguesePluralTests(unittest.TestCase):
    def test_regular_and_irregular_forms(self):
        self.assertEqual(plurale_pt_br.plural_word("Espada"), "Espadas")
        self.assertEqual(plurale_pt_br.plural_word("missão"), "missões")
        self.assertEqual(plurale_pt_br.plural_word("alemão"), "alemães")
        self.assertEqual(plurale_pt_br.plural_word("cão"), "cães")

    def test_adds_guild_wars_plural_markup(self):
        translated, result, _changes = plurale_pt_br.make_plural("Espada", "Sword[s]")
        self.assertEqual(translated, 'Espada[pl:"Espadas"]')
        self.assertEqual(result, "ok")

    def test_agrees_plural_article_and_noun(self):
        translated, _result, _changes = plurale_pt_br.make_plural("A Espada", "A Sword[s]")
        self.assertEqual(translated, 'A[pl:"As"] Espada[pl:"Espadas"]')

    def test_portuguese_recipe_prefix_and_article_cleanup(self):
        self.assertEqual(lt_server.recipe_split("Recipe: Iron Sword"),
                         ("Receita: ", "Iron Sword", ""))
        self.assertEqual(lt_server.drop_article("A Espada", "Iron Sword"), "Espada")
        self.assertEqual(lt_server.drop_article("A Espada", "The Sword"), "A Espada")


if __name__ == "__main__":
    unittest.main()