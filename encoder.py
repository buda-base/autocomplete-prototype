from typing import List, Dict, Tuple

# from https://github.com/OpenPecha/CommonSpell/blob/main/src/CommonSpell/encoder.py

GAP_ELEMENT = ''

class Encoder(object):
    """
    Simple encoder class. A encoder just assigns integers to tokens (in our case strings).
    This significantly speeds up operations and allows working at the token level instead of
    character level.
    """
    def __init__(self, allow_decode=False, shift=32, split_code_for_2_bytes=False):
        """
        shift: gives the minimum code value. 32 is the default to avoid ASCII control codes.
               we also add 10 to this value to account for the possibility of splitting codes on 2 characters.

        split_code_for_2_bytes: In some cases encoding high code values as characters won't work
        for diff_match_patch, making it raise an exception. This happens mostly on Windows, see
        https://github.com/JoshData/fast_diff_match_patch/blob/5f7b0143353e7419e9f4d6253ac9d206a1369683/interface.cpp#L180
        """
        self.elementToCode: Dict[str,int] = {GAP_ELEMENT: shift}
        if allow_decode:
            self.codeToElement: List[str] = [None for _ in range(shift+10)]
            self.codeToElement.append(GAP_ELEMENT)
        self.last: int = shift+10
        self.allow_decode = allow_decode
        self.shift = shift
        self.split_code_for_2_bytes = split_code_for_2_bytes

    def has(self, element: str) -> bool:
        return element in self.elementToCode

    def hasCode(self, code: int) -> bool:
        return code <= self.last

    def encode(self, element: str) -> int:
        code = self.elementToCode.get(element)
        if code is None:
            self.last += 1
            code = self.last
            self.elementToCode[element] = code
            if self.allow_decode:
                self.codeToElement.append(element)
        # if self.last >= 65536, things can be complicated on Windows
        return code

    def encode_str(self, element: str) -> Tuple[str,int]:
        code: int = self.encode(element)
        # if the code is more than 65536, it's not possible to 
        # 
        if not self.split_code_for_2_bytes or code < 65536:
            return chr(code), 1
        else:
            # first_char_code will be in the range self.shift -> self.shift+10
            # (at least in the likely situations)
            first_char_code = (code // 65536) + self.shift
            # the second char code should start after self.shift + 10
            second_char_code = (code % 65536) + self.shift + 10 
            return chr(first_char_code)+chr(second_char_code), 2

    def encode_list(self, element_list: List[str]):
        res = ""
        for e in element_list:
            s, nb_c = self.encode_str(e)
            res += s
        return res

    def decode(self, code: int) -> str:
        if not self.allow_decode:
            raise KeyError('encoder does not allow decoding')
        try:
            return self.codeToElement[code]
        except KeyError:
            raise KeyError(
                'there is no elements in the encoder encoded as %d' % code)

    def decode_string(self, s: str):
        res = ""
        for c in s:
            decoded_c = self.decode(ord(c))
            res += decoded_c
        return res

    def elements(self):
        return [self.decode(c) for c in sorted(self.codeToElement)]

    def len(self):
        return self.last + 1

    def reset(self):
        self.elementToCode: Dict[str,int] = {GAP_ELEMENT: self.shift+10}
        if self.allow_decode:
            self.codeToElement: List[str] = [None for _ in range(self.shift+10)]
            self.codeToElement.append(GAP_ELEMENT)
        self.last: int = self.shift+10