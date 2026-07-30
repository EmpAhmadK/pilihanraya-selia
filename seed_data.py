"""
Run this once (e.g. `python3 seed_data.py`) to pre-populate elections.json
with the Negeri Sembilan election and its 36 constituencies, instead of
typing all of them into the "add election" form by hand.

Feel free to edit ELECTION_NAME / ELECTION_QID below first.
"""
import storage

ELECTION_NAME = "Pilihan Raya Negeri Sembilan"
ELECTION_QID = "Q139747429"

SEATS = [
    {"kod": "N01", "nama": "Chennah", "qid": "Q140546215"},
    {"kod": "N02", "nama": "Pertang", "qid": "Q140546216"},
    {"kod": "N03", "nama": "Sungai Lui", "qid": "Q140546217"},
    {"kod": "N04", "nama": "Klawang", "qid": "Q140546218"},
    {"kod": "N05", "nama": "Serting", "qid": "Q140546219"},
    {"kod": "N06", "nama": "Palong", "qid": "Q140546220"},
    {"kod": "N07", "nama": "Jeram Padang", "qid": "Q140546221"},
    {"kod": "N08", "nama": "Bahau", "qid": "Q140546222"},
    {"kod": "N09", "nama": "Lenggeng", "qid": "Q140546223"},
    {"kod": "N10", "nama": "Nilai", "qid": "Q140546224"},
    {"kod": "N11", "nama": "Lobak", "qid": "Q140546225"},
    {"kod": "N12", "nama": "Temiang", "qid": "Q140546227"},
    {"kod": "N13", "nama": "Sikamat", "qid": "Q140546228"},
    {"kod": "N14", "nama": "Ampangan", "qid": "Q140546230"},
    {"kod": "N15", "nama": "Juasseh", "qid": "Q140546231"},
    {"kod": "N16", "nama": "Seri Menanti", "qid": "Q140546232"},
    {"kod": "N17", "nama": "Senaling", "qid": "Q140546233"},
    {"kod": "N18", "nama": "Pilah", "qid": "Q140546234"},
    {"kod": "N19", "nama": "Johol", "qid": "Q140546235"},
    {"kod": "N20", "nama": "Labu", "qid": "Q140546236"},
    {"kod": "N21", "nama": "Bukit Kepayang", "qid": "Q140546237"},
    {"kod": "N22", "nama": "Rahang", "qid": "Q140546238"},
    {"kod": "N23", "nama": "Mambau", "qid": "Q140546239"},
    {"kod": "N24", "nama": "Seremban Jaya", "qid": "Q140546240"},
    {"kod": "N25", "nama": "Paroi", "qid": "Q140546241"},
    {"kod": "N26", "nama": "Chembong", "qid": "Q140546243"},
    {"kod": "N27", "nama": "Rantau", "qid": "Q140546244"},
    {"kod": "N28", "nama": "Kota", "qid": "Q140546245"},
    {"kod": "N29", "nama": "Chuah", "qid": "Q140546246"},
    {"kod": "N30", "nama": "Lukut", "qid": "Q140546247"},
    {"kod": "N31", "nama": "Bagan Pinang", "qid": "Q140546248"},
    {"kod": "N32", "nama": "Linggi", "qid": "Q140546249"},
    {"kod": "N33", "nama": "Sri Tanjung", "qid": "Q140546250"},
    {"kod": "N34", "nama": "Gemas", "qid": "Q140546251"},
    {"kod": "N35", "nama": "Gemencheh", "qid": "Q140546253"},
    {"kod": "N36", "nama": "Repah", "qid": "Q140546254"},
]

if __name__ == "__main__":
    storage.save_election(ELECTION_QID, ELECTION_NAME, SEATS)
    print(f"Saved '{ELECTION_NAME}' ({ELECTION_QID}) with {len(SEATS)} seats.")
