# bard_token = ConfigHandler().get_item_protected(key="bard_api_key")
#         res = None
#
#         if bard_token == "" or bard_token is None:
#             logger.warning("Invalid bard token, can't concatenate captions.")
#         else:
#             try:
#                 logger.debug("Using bard token: " + bard_token)
#                 bard = Bard(token=bard_token)
#                 question = '''
# Let's play a game. I'm going to give you some descriptive words, and I want you to use them to create a caption that can
# be used for diffusion training. The caption should consist of multiple tokens separated by commas, with one long primary
# token/sentence at the beginning, followed by multiple detail tokens separated by commas.
#
# You should use every detail provided, trying to avoid repeating words.
#
# This caption should be formatted like so:
#
# RESPONSE=a primary sentence to describe the subject, descriptive token, descriptive token, descriptive token
#
# As an example: "A young caucasian woman wearing an orange dress standing in the street, city, blonde hair, sepia, photograph"
# Or: "A man wearing a black suit and tie standing in front of a white wall, portrait, black and white, photograph"
#
# Be sure to include the word RESPONSE at the beginning of your caption, and separate each detail with a comma.
#
# Here is the data:
#                 '''
#                 for key, value in outputs.items():
#                     value = value[0].replace("nude", "").strip()
#                     value = value.replace("naked", "").strip()
#                     question += f"\n{key}: {value} "
#                 logger.debug(f"Asking: {question}")
#                 answer = bard.get_answer(question)['content']
#                 # Read each line of the answer and find the first line that starts with RESPONSE=
#                 answer = answer.split("\n")
#                 res = None
#                 for line in answer:
#                     if "RESPONSE=" in line:
#                         res = line.split("=")[1].replace("*", "").strip()
#                         break
#                 logger.debug(f"Answer: {res}")
#             except Exception as e:
#                 logger.warning("Failed to get answer from bard.")
#                 traceback.print_exc()
