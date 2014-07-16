"""Unit tests for the collectionprocessor module.
"""

import mock
import os
import unittest

from lib.wordseerbackend.wordseerbackend import collectionprocessor
from app import app
from app.models.document import Document
from lib.wordseerbackend.wordseerbackend.parser import documentparser
from lib.wordseerbackend.wordseerbackend.sequence import sequenceprocessor
from lib.wordseerbackend.wordseerbackend import stringprocessor
from lib.wordseerbackend.wordseerbackend import structureextractor
from lib.wordseerbackend.wordseerbackend import logger

def setUpModule():
    global mock_writer
    mock_writer = mock.MagicMock(name="Mock Reader Writer")
    with mock.patch(
        "lib.wordseerbackend.wordseerbackend.collectionprocessor.StringProcessor",
        autospec=stringprocessor.StringProcessor):
        global colproc
        colproc = collectionprocessor.CollectionProcessor(mock_writer)

@mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.logger", autospec=logger)
class TestCollectionProcessor(unittest.TestCase):
    """Test the CollectionProcessor class.
    """
    @mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.structureextractor",
        autospec=structureextractor)
    @mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.os", autospec=os)
    def test_extract_record_metadata(self, mock_os, mock_strucex, mock_logger):
        """Test the extract_record_metadata method.
        """
        # Set up the input objects
        collection_dir = "/foobar/"
        docstruc_filename = mock.create_autospec(str)
        filename_extension = ".xml"
        files = ["file1.xml", "file2.XmL", "file3.foo", ".file4.xml"]

        # Configure the mock os
        mock_os.listdir.return_value = files
        mock_os.path.splitext.side_effect = os.path.splitext
        mock_os.path.join.side_effect = os.path.join

        # Configure mock logger
        mock_logger.get.return_value = ""

        # Make the structure extractor return useful objects
        extracted_docs = [
            (os.path.join(collection_dir, files[0]),
                [mock.create_autospec(Document) for x in range(10)]),
            (os.path.join(collection_dir, files[1]),
                [mock.create_autospec(Document) for x in range(10)])
        ]

        def extract_docs(filename):
            for entry in extracted_docs:
                if entry[0] == filename:
                    return entry[1]

        mock_strucex_instance = mock_strucex.StructureExtractor("", "")
        mock_strucex_instance.extract.side_effect = extract_docs

        # Run the SUT
        colproc.extract_record_metadata(collection_dir, docstruc_filename,
            filename_extension)

        # logger.log() should have been called twice for each file like this
        log_calls = []

        for i in range(0, 2):
            log_calls.append(mock.call("finished_recording_text_and_metadata",
                "false", mock_logger.REPLACE))
            log_calls.append(mock.call("text_and_metadata_recorded", str(i + 1),
                mock_logger.UPDATE))

        log_calls.append(mock.call("finished_recording_text_and_metadata",
                "true", mock_logger.REPLACE))
        mock_logger.log.assert_has_calls(log_calls)

        # The extractor should have been called on each file
        strucex_calls = [mock.call(extracted_docs[0][0]),
            mock.call(extracted_docs[1][0])
        ]
        for call in strucex_calls:
            self.failUnless(call in mock_strucex_instance.extract.\
                call_args_list)

        # The reader writer should be called on every extracted doc
        createdoc_calls = []
        num_done = 1
        for entry in extracted_docs:
            for doc in entry[1]:
                createdoc_calls.append(mock.call(doc, num_done))
            num_done += 1
        mock_writer.create_new_document.assert_has_calls(createdoc_calls)

    @mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.DocumentParser",
        autospec=documentparser.DocumentParser)
    def test_parse_documents(self, mock_dp, mock_logger):
        """Tests for the test_parse_documents method.
        """
        # Set up the mocks
        max_doc = 20
        mock_writer.list_document_ids.return_value = range(max_doc)
        mock_dp_instance = mock_dp("", "")

        mock_gotten_doc = mock.create_autospec(Document)
        mock_writer.get_document.return_value = mock_gotten_doc

        latest = 5
        mock_logger.get.return_value = str(latest)

        # Run the SUT
        colproc.parse_documents()

        # Reader writer should have been called for every id greater than
        # what the logger returned and once at the end
        get_doc_calls = [mock.call(x) for x in range(latest + 1, max_doc)]
        mock_writer.get_document.assert_has_calls(get_doc_calls)
        mock_writer.finish_grammatical_processing.assert_called_once()

        # Document parser should have been called on every doc
        parse_calls = [mock.call(mock_gotten_doc)
            for x in range(latest + 1, max_doc)]
        mock_dp_instance.parse_document.assert_has_calls(parse_calls)

        # Logger should be called twice per doc
        logger_calls = []
        for i in range(latest + 1, max_doc):
            logger_calls.append(mock.call("finished_grammatical_processing",
                "false", mock_logger.REPLACE))
            logger_calls.append(mock.call("latest_parsed_document_id",
                str(i), mock_logger.REPLACE))
        mock_logger.log.assert_has_calls(logger_calls)

    @mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.SequenceProcessor",
        autospec=sequenceprocessor.SequenceProcessor)
    def test_calculate_index_sequences(self, mock_seq_proc, mock_logger):
        """Tests for the calculate_index_sequences method.
        """
        # Set up the mocks
        latest = 5
        mock_logger.get.return_value = str(latest)

        max_id = 20
        mock_writer.get_max_sentence_id.return_value = max_id

        sentences = [mock.MagicMock(words=range(10), id=x)
            for x in range(0, max_id)]

        def get_sentence(arg):
            return sentences[arg]

        mock_writer.get_sentence.side_effect = get_sentence

        mock_seq_proc_instance = mock_seq_proc("")
        mock_seq_proc_instance.process.return_value = True

        # Run the SUT
        colproc.calculate_index_sequences()

        # Reader writer should have been called once
        mock_writer.load_sequence_counts.assert_called_once()

        # Sequence processor called for every sentence
        seq_proc_calls = [mock.call(sentences[i])
            for i in range(latest + 1, max_id)]
        mock_seq_proc_instance.process.assert_has_calls(seq_proc_calls)

        # Logger should be called twice a sentence
        logger_calls = []
        for i in range(latest + 1, max_id):
            logger_calls.append(mock.call("finished_sequence_processing",
                "false", mock_logger.REPLACE))
            logger_calls.append(mock.call("latest_sequence_sentence",
                str(i), mock_logger.REPLACE))
        mock_logger.log.assert_has_calls(logger_calls)

class TestCollectionProcessorProcess(unittest.TestCase):
    """Tests specifically for CollectionProcessor.process().
    """
    def setUp(self):
        colproc.calculate_index_sequences = mock.create_autospec(
            colproc.calculate_index_sequences)
            #name="calc_index_sequences",)
        colproc.parse_documents = mock.create_autospec(
            colproc.parse_documents)
            #name="parse_documents",)
        colproc.extract_record_metadata = mock.create_autospec(
            colproc.extract_record_metadata)
            #name="extract_record_metadata",)

        # Set up the dict that is our "logging database" and set the arguments
        # for calling process()
        self.log_dict = {"finished_recording_text_and_metadata": "true",
            "finished_grammatical_processing": "true",
            "finished_sequence_processing": "true",
            "word_counts_done": "true",
            "tfidf_done": "true",
            "word_similarity_calculations_done": "true"
        }

        self.args = ["", "", "", False]

        # Reset the previously used mocks
        mock_writer.reset_mock()

    @mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.logger", autospec=logger)
    def test_process_e_r_m(self, mock_logger):
        """Test that extract_record_metadata() is called properly.
        """
        mock_logger.get.side_effect = self.log_dict.__getitem__
        # Should just extract_record_metadata
        self.log_dict["finished_recording_text_and_metadata"] = "false"

        mock_config = {
            "SEQUENCE_INDEXING": False,
            "PART_OF_SPEECH_TAGGING": False,
            "GRAMMATICAL_PROCESSING": False,
        }

        with mock.patch.dict(app.config, mock_config):
            colproc.process(*self.args)

        assert colproc.extract_record_metadata.called
        assert colproc.calculate_index_sequences.called == False
        assert colproc.parse_documents.called == False
        assert len(colproc.reader_writer.method_calls) == 0

    @mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.logger", autospec=logger)
    def test_process_parse_documents(self, mock_logger):
        """Test that parse_documents is called properly
        """
        mock_logger.get.side_effect = self.log_dict.__getitem__

        # Should only run parse_documents
        self.log_dict["finished_grammatical_processing"] = "false"

        mock_config = {
            "SEQUENCE_INDEXING": False
        }

        with mock.patch.dict(app.config, mock_config):
            colproc.process(*self.args)

        assert colproc.parse_documents.call_count == 1
        assert colproc.calculate_index_sequences.called == False
        assert colproc.extract_record_metadata.called == False
        assert len(colproc.reader_writer.method_calls) == 0

    @mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.logger", autospec=logger)
    def test_process_calc_index_sequences(self, mock_logger):
        """Test that calculate_index_sequences() is called along with
        the reader_writer.
        """
        mock_logger.get.side_effect = self.log_dict.__getitem__

        # Should run calculate_index_sequences() and run the reader_writer
        colproc.process(*self.args)

        assert colproc.calculate_index_sequences.call_count == 1
        assert mock_writer.finish_indexing_sequences.call_count == 1
        assert len(mock_writer.method_calls) == 1
        assert colproc.parse_documents.called == False
        assert colproc.extract_record_metadata.called == False

    @mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.logger", autospec=logger)
    def test_process_calc_word_counts(self, mock_logger):
        """Test that ReaderWriter.calculate_word_counts() is called along with
        the logs being updated.
        """
        mock_logger.get.side_effect = self.log_dict.__getitem__

        self.log_dict["word_counts_done"] = "false"
        self.log_dict["finished_sequence_processing"] = "false"
        colproc.process(*self.args)

        assert mock_writer.calculate_word_counts.call_count == 1
        assert len(mock_writer.method_calls) == 1
        assert colproc.calculate_index_sequences.called == False
        assert colproc.parse_documents.called == False
        assert colproc.extract_record_metadata.called == False
        mock_logger.log.assert_called_once_with("word_counts_done", "true",
            mock_logger.REPLACE)

    @mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.logger", autospec=logger)
    def test_process_tfidfs(self, mock_logger):
        """Test that ReaderWriter.calculate_tfidfs() is called.
        """
        mock_logger.get.side_effect = self.log_dict.__getitem__

        self.log_dict["tfidf_done"] = "false"
        self.log_dict["finished_sequence_processing"] = "false"
        colproc.process(*self.args)

        assert mock_writer.calculate_tfidfs.call_count == 1
        assert len(mock_writer.method_calls) == 1
        assert colproc.calculate_index_sequences.called == False
        assert colproc.parse_documents.called == False
        assert colproc.extract_record_metadata.called == False

    @mock.patch("lib.wordseerbackend.wordseerbackend.collectionprocessor.logger", autospec=logger)
    def test_process_w2w(self, mock_logger):
        """Test that calculate_lin_similarities() is run.
        """
        mock_logger.get.side_effect = self.log_dict.__getitem__

        self.log_dict["word_similarity_calculations_done"] = "false"
        self.log_dict["finished_sequence_processing"] = "false"
        colproc.process(*self.args)

        assert mock_writer.calculate_lin_similarities.call_count == 1
        assert len(mock_writer.method_calls) == 1
        assert colproc.calculate_index_sequences.called == False
        assert colproc.parse_documents.called == False
        assert colproc.extract_record_metadata.called == False
