import pathlib
import logging
from dataclasses import dataclass
from PIL import Image
import os
from captionr.blip_cap import BLIP
from captionr.clip_interrogator import Interrogator, Config
from captionr.coca_cap import Coca
from captionr.git_cap import Git
from captionr.qwen_cap import QwenCap
import torch
import re
from thefuzz import fuzz

@dataclass
class CaptionrConfig:
    folder = None
    output: pathlib.Path = None
    existing = 'skip'
    cap_length = 150
    git_pass = False
    coca_pass = False
    blip_pass = False
    qwen_pass = False
    model_order = 'coca,git,blip,qwen'
    use_blip2 = False
    blip2_model = None
    blip2_question_file:pathlib.Path = None
    blip2_questions = []
    blip_beams = 64
    blip_min = 30
    blip_max = 75
    clip_model_name = 'ViT-H-14/laion2b_s32b_b79k'
    clip_flavor = False
    clip_max_flavors = 8
    clip_artist = False
    clip_medium = False
    clip_movement = False
    clip_trending = False
    clip_method = 'interrogate_fast'
    fail_phrases = 'a sign that says,writing that says,that says,with the word'
    ignore_tags = ''
    find = ''
    replace = ''
    folder_tag = False
    folder_tag_levels = 1
    folder_tag_stop: pathlib.Path = None
    preview = False
    use_filename = False
    append_text = ''
    prepend_text = ''
    uniquify_tags = False
    device = ("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")
    extension = 'txt'
    quiet = False
    debug = False
    base_path = os.path.dirname(__file__)
    fuzz_ratio = 60.0
    _blip:BLIP = None
    _qwen:QwenCap = None
    _clip:Interrogator = None
    _coca:Coca = None
    _git:Git = None
    qwen_chat_text = "describe this image"


class Captionr:
    def __init__(self, config:CaptionrConfig) -> None:
        self.config = config

    def get_parent_folder(self, filepath, levels=1):
        common = os.path.split(filepath)[0]
        paths = []
        for i in range(int(levels)):
            split = os.path.split(common)
            common = split[0]
            
            paths.append(split[1])

            if self.config.folder_tag_stop is not None and \
                    self.config.folder_tag_stop != '' and \
                    split[0] == self.config.folder_tag_stop:
                break
        return paths

    def process_img(self,img_path):
        config = self.config
        try:
            # Load image
            with Image.open(img_path).convert('RGB') as img:
                # Get existing caption
                existing_caption = ''
                cap_file = os.path.join(os.path.dirname(img_path),os.path.splitext(os.path.split(img_path)[1])[0] + f'.{config.extension}')
                if os.path.isfile(cap_file):
                    try:
                        with open(cap_file) as f:
                            existing_caption = f.read()
                    except Exception as e:
                        logging.exception(f"Got exception reading caption file: {e}")

                # Get caption from filename if empty
                if existing_caption == '' and config.use_filename:
                    path = os.path.split(img_path)[1]
                    path = os.path.splitext(path)[0]
                    existing_caption = ''.join(c for c in path if c.isalpha() or c in [" ", ","])
                
                
                # Create tag list
                out_tags = []
                new_caption = existing_caption
                
                logging.info("Let me be clear")
                logging.info(config.model_order.split(','))
                # got_cap = False
                model_captions ={}
                for m in config.model_order.split(','):
                    model_caption = None
                    if m == 'git' and config.git_pass and config._git is not None:
                        logging.debug('Getting GIT caption')
                        logging.info('Git was called tho')
                        try:
                            model_caption = config._git.caption(img)
                        except:
                            logging.exception("Exception during GIT captioning")
                            # continue
                        logging.debug(f'GIT Caption: {new_caption}')
                        if any(f in new_caption for f in config.fail_phrases.split(',')):
                            logging.info(f'GIT caption was\n{new_caption}\nFail phrases detected.')
                        # else:
                        #     got_cap = True
                        #     break
                    if m == 'coca' and config.coca_pass and config._coca is not None:
                        logging.debug('Getting Coca caption')
                        try:
                            model_caption = config._coca.caption(img)
                        except:
                            logging.exception("Exception during Coca captioning")
                            # continue
                        logging.debug(f'Coca Caption: {new_caption}')
                        if any(f in new_caption for f in config.fail_phrases.split(',')):
                            logging.info(f'Coca caption was\n{new_caption}\nFail phrases detected.')
                        # else:
                        #     got_cap = True
                        #     break
                    if m == 'blip' and config.blip_pass and config._blip is not None:
                        logging.debug('Getting BLIP caption')
                        try:
                            model_caption = config._blip.caption(img)
                        except:
                            logging.exception("Exception during BLIP captioning")
                            # continue
                        logging.debug(f'BLIP Caption: {new_caption}')
                        if any(f in new_caption for f in config.fail_phrases.split(',')):
                            logging.info(f'BLIP caption was\n{new_caption}\nFail phrases detected.')
                        # else:
                            # got_cap = True
                            # break
                    if m == 'qwen' and config.qwen_pass and config._qwen is not None:
                        logging.debug('Getting Qwen caption')
                        try:
                            model_caption = config._qwen.chat(img_path, config.qwen_chat_text)
                        except:
                            logging.exception("Exception during Qwen captioning")
                        logging.debug(f'Qwen Caption: {new_caption}')
                        if any(f in new_caption for f in config.fail_phrases.split(',')):
                            logging.info(f'Qwen caption was\n{new_caption}\nFail phrases detected.')
                    model_captions[m] = model_caption
                # Strip period from end of caption

                print(model_captions)
                new_caption = ' '.join([model_captions[key] for key in model_captions])
                
                
                print(new_caption)
                matches = re.match('^.+(\s+\.\s*)$',new_caption)
                if matches is not None:
                    new_caption = new_caption[:-(len(matches.group(1)))].strip()

                # Add enabled CLIP flavors to tag list
                if (config.clip_artist or config.clip_flavor or config.clip_trending or config.clip_movement or config.clip_medium) and config._clip is not None:
                    func = getattr(config._clip,config.clip_method)
                    tags = func(caption=new_caption, image=img, max_flavors=config.clip_max_flavors)
                    logging.debug(f'CLIP tags: {tags}')

                    for tag in tags.split(","):
                        out_tags.append(tag.strip())
                else:
                    for tag in new_caption.split(","):
                        out_tags.append(tag.strip())

                # BLIP2 questions
                # if config.use_blip2 and config.blip2_questions is not None and len(config.blip2_questions) > 0:
                #     image = config._blip.processor["eval"](img).unsqueeze(0).to(config._blip.device)

                #     for q in config.blip2_questions:
                #         tag = config._blip.question(image,q)
                #         out_tags.append(tag.strip())

                # Add parent folder to tag list if enabled
                if config.folder_tag:
                    folder_tags = self.get_parent_folder(img_path,config.folder_tag_levels)
                    for tag in folder_tags:
                        out_tags.append(tag.strip())

                # Remove duplicates, filter dumb stuff
                # chars_to_strip = ["_\\("]
                unique_tags = []
                tags_to_ignore = []
                if config.ignore_tags != "" and config.ignore_tags is not None:
                    si_tags = config.ignore_tags.split(",")
                    for tag in si_tags:
                        tags_to_ignore.append(tag.strip())

                if config.uniquify_tags:
                    for tag in out_tags:
                        tstr = tag.strip()
                        if not tstr in unique_tags and not "_\(" in tag and  tstr not in tags_to_ignore:
                            should_append = True
                            for s in unique_tags:
                                if fuzz.ratio(s,tstr) > self.config.fuzz_ratio:
                                    should_append = False
                                    break
                            if should_append:
                                unique_tags.append(tag.replace('"','').strip())
                else:
                    for tag in out_tags:
                        if not "_\(" in tag and tag.strip() not in tags_to_ignore:
                            unique_tags.append(tag.replace('"','').strip())
                logging.debug(f'Unique tags (before existing): {unique_tags}')
                logging.debug(f'Out Tags: {out_tags}')

                existing_tags = existing_caption.split(",")
                logging.debug(f'Existing Tags: {existing_tags}')

                # APPEND/PREPEND/OVERWRITE existing caption based on options
                if config.existing == "prepend" and len(existing_tags):
                    new_tags = existing_tags
                    for tag in unique_tags:
                        if not tag.strip() in new_tags or not config.uniquify_tags:
                            new_tags.append(tag.strip())
                    unique_tags = new_tags

                if config.existing == 'append' and len(existing_tags):
                    for tag in existing_tags:
                        if not tag.strip() in unique_tags or not config.uniquify_tags:
                            unique_tags.append(tag.strip())

                if config.existing == 'copy' and existing_caption:
                    for tag in existing_tags:
                        unique_tags.append(tag.strip())

                try:
                    unique_tags.remove('')
                except ValueError:
                    pass

                logging.debug(f'Unique tags: {unique_tags}')
                # Construct new caption from tag list
                caption_txt = ", ".join(unique_tags)

                if config.find is not None and config.find != '' and config.replace is not None and config.replace != '':
                    # Find and replace "a SUBJECT CLASS" in caption_txt with subject name
                    if f"{config.find}" in caption_txt:
                        caption_txt = caption_txt.replace(f"{config.find}", config.replace)


                tags = caption_txt.split(" ")
                if config.cap_length != 0 and len(tags) > config.cap_length:
                        tags = tags[0:config.cap_length]
                        tags[-1] = tags[-1].rstrip(",")
                caption_txt = " ".join(tags)

                if config.append_text != '' and config.append_text is not None:
                    caption_txt = caption_txt + config.append_text
                
                if config.prepend_text != '' and config.prepend_text is not None:
                    caption_txt = config.prepend_text.rstrip().lstrip() + ' ' + caption_txt
                
                outputfilename = ''
                # Write caption file
                if not config.preview:
                    if config.output == '' or config.output is None:

                        dirname = os.path.dirname(cap_file)  
                    else: 
                        if config.output is [pathlib.PosixPath]:
                            dirname = str(config.output[0])
                        else:
                            dirname = str(config.output)
                    
                    outputfilename = os.path.join(dirname,os.path.basename(cap_file))
                    with open(outputfilename, "w", encoding="utf8") as file:
                        file.write(caption_txt)
                        logging.debug(f'Wrote {outputfilename}')

                if config.preview:
                    logging.info(f'PREVIEW: {caption_txt}')
                    logging.info('No caption file written.')
                else:
                    logging.info(f'{outputfilename}: {caption_txt}')
            
                return caption_txt
        except Exception as e:
            logging.exception(f"Exception occurred processing {img_path}")