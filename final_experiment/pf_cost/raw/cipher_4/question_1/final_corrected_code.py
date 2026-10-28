# pf_cipher_4_0.py

def _build_maps(polybius_rows):
    """
    polybius_rows: list[str], length 5; each string length 5.
      Example row1 'RTXFS' means:
        (1,1)->R, (1,2)->T, ..., (1,5)->S
    Returns:
      enc_map: dict[str, str]  letter -> "rc"
      dec_map: dict[str, str]  "rc" -> letter
    Note:
      'O' is not in the square; encryption maps 'O' -> '66', decryption maps '66' -> 'O'.
    """
    if not isinstance(polybius_rows, list) or len(polybius_rows) != 5:
        raise ValueError("polybius_rows must be a list of 5 strings.")
    for r in polybius_rows:
        if not isinstance(r, str) or len(r) != 5:
            raise ValueError("each row in polybius_rows must be a string of length 5.")

    enc_map = {}
    dec_map = {}
    for i in range(5):          # row index 0..4
        for j in range(5):      # col index 0..4
            ch = polybius_rows[i][j]
            rc = f"{i+1}{j+1}"
            enc_map[ch] = rc
            dec_map[rc] = ch
    return enc_map, dec_map


def polybius_encrypt(plaintext, polybius_rows):
    """
    Encrypt plaintext (uppercase letters) to digit string with the given Polybius square.
    Special rule: 'O' -> '66'.
    """
    enc_map, _ = _build_maps(polybius_rows)
    res = []
    for ch in plaintext:
        if ch == "O":
            res.append("66")
        else:
            if ch not in enc_map:
                raise ValueError(f"character {ch} not in Polybius square and not 'O'.")
            res.append(enc_map[ch])
    return "".join(res)


def polybius_decrypt(ciphertext, polybius_rows):
    """
    Decrypt digit string to plaintext with the given Polybius square.
    Ciphertext length must be even; parse as pairs.
    Special rule: '66' -> 'O'.
    """
    _, dec_map = _build_maps(polybius_rows)
    if len(ciphertext) % 2 != 0:
        raise ValueError("ciphertext length must be even (pairs of digits).")

    res = []
    for i in range(0, len(ciphertext), 2):
        pair = ciphertext[i:i+2]
        if pair == "66":
            res.append("O")
        else:
            if pair not in dec_map:
                raise ValueError(f"pair {pair} not decodable by Polybius square.")
            res.append(dec_map[pair])
    return "".join(res)