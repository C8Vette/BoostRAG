import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import chunk_embed


def test_rebuild_chroma_collection_deletes_and_rebuilds():
    fake_doc = {
        "brand": "VRSF",
        "category": "Downpipe",
        "product": "VRSF Catted Downpipe B58 M340i",
        "vehicle": "BMW M340i G20",
        "source_type": "product_page",
        "url": "https://example.com/product",
        "price": "$499.00",
        "source_file": "fake.txt",
        "text": "A" * 1500,  # long enough to produce multiple chunks
    }

    mock_collection = MagicMock()
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    with patch.object(chunk_embed, "chromadb") as mock_chromadb, \
         patch.object(chunk_embed, "load_documents", return_value=[fake_doc]) as mock_load, \
         patch.object(chunk_embed, "get_embedding", return_value=[0.0, 0.1, 0.2]) as mock_embed:
        mock_chromadb.PersistentClient.return_value = mock_client

        count = chunk_embed.rebuild_chroma_collection()

    mock_client.delete_collection.assert_called_once_with(name=chunk_embed.COLLECTION_NAME)
    mock_load.assert_called_once()
    assert count > 0
    mock_collection.upsert.assert_called_once()
