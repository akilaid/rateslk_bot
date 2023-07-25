import telebot
import json
import time
import signal
import sys
import os
import datetime
import threading
import random
import logging

logging.basicConfig(level=logging.ERROR)

with open('bot_token.txt', 'r') as file:
    TOKEN = file.readline().strip()

bot = telebot.TeleBot(TOKEN)

with open('admins.json') as json_file:
    data = json.load(json_file)

admins = data['admins']

# Inline keyboard markup with four buttons
keyboard = telebot.types.InlineKeyboardMarkup()
button_deriv = telebot.types.InlineKeyboardButton("Deriv", callback_data="deriv")
button_skrill = telebot.types.InlineKeyboardButton("SKRILL", callback_data="skrill")
button_usdt = telebot.types.InlineKeyboardButton("USDT", callback_data="usdt")
button_payoneer = telebot.types.InlineKeyboardButton("Payoneer", callback_data="payoneer")
keyboard.row(button_deriv, button_skrill, button_usdt, button_payoneer)

start_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
start_keyboard.row("/update", "/rates")
start_keyboard.row("/admin")  # Add the /admin command to the keyboard

# Load existing data from JSON file
data = []
with open('/var/www/html/data.json', 'r') as json_file:
    data = json.load(json_file)

# Dictionary to store rates
user_rates = {}

@bot.message_handler(commands=['update'])
def handle_update(message):
    if message.chat.username in admins:
        bot.reply_to(message, 'Please select an option:', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        if call.data == "deriv":
            bot.send_message(call.message.chat.id, "Enter Selling rate for Deriv:")
            bot.register_next_step_handler(call.message, get_selling_rate, 1)  # ID for Deriv is 1
        elif call.data == "skrill":
            bot.send_message(call.message.chat.id, "Enter Selling rate for SKRILL:")
            bot.register_next_step_handler(call.message, get_selling_rate, 2)  # ID for SKRILL is 2
        elif call.data == "usdt":
            bot.send_message(call.message.chat.id, "Enter Selling rate for USDT:")
            bot.register_next_step_handler(call.message, get_selling_rate, 3)  # ID for USDT is 3
        elif call.data == "payoneer":
            bot.send_message(call.message.chat.id, "Enter Selling rate for Payoneer:")
            bot.register_next_step_handler(call.message, get_selling_rate, 4)  # ID for Payoneer is 4
        elif call.data == "add_admin":
            bot.send_message(call.message.chat.id, "Please enter the username of the user you want to add as an admin:")
            bot.register_next_step_handler(call.message, add_new_admin_from_callback)
        elif call.data == "remove_admin":
            bot.send_message(call.message.chat.id, "Please enter the username of the user you want to remove as an admin:")
            bot.register_next_step_handler(call.message, remove_admin_from_callback)
        elif call.data == "view_admins":
            if call.message.chat.username in admins:
                admins_list = "\n".join(admins)
                bot.send_message(call.message.chat.id, f"Current Admins:\n{admins_list}")
            else:
                bot.send_message(call.message.chat.id, "You don't have permission to access this command.")
        elif call.data == "add_post":
            if call.message.chat.username in admins:
                bot.send_message(call.message.chat.id, "Please send an image to add as a post:")
                bot.register_next_step_handler(call.message, save_image_as_post)
        elif call.data == "remove_post":
            # Get the list of post filenames from the 'posts/' folder
            post_filenames = get_post_filenames()
            if post_filenames:
                # Send the list of file names for the user to select
                send_file_names_for_removal(call.message.chat.id, post_filenames)
                bot.register_next_step_handler(call.message, remove_image_from_posts, post_filenames)
            else:
                bot.send_message(call.message.chat.id, "No posts available to remove.")
        else:
            bot.send_message(call.message.chat.id, "❌ An error occurred while processing your request.")
    except Exception as e:
        logging.exception("Error in handle_callback:")
        bot.send_message(call.message.chat.id, "❌ An error occurred while processing your request.")

def send_file_names_for_removal(chat_id, post_filenames):
    try:
        if not post_filenames:
            bot.send_message(chat_id, "No posts available to remove.")
            return

        # Send the initial message prompting the user to enter the filename
        bot.send_message(chat_id, "Please enter the filename of the image you want to remove:")

        # Loop through the post_filenames list and send each filename as a separate message
        for file_name in post_filenames:
            bot.send_message(chat_id, file_name)

    except Exception as e:
        logging.exception("Error in send_file_names_for_removal:")
        bot.send_message(chat_id, "❌ An error occurred while processing your request.")

def get_selling_rate(message, currency_id):
    try:
        selling_rate = round(float(message.text), 2)
        user_rates[currency_id] = {"selling_rate": selling_rate}
        bot.send_message(message.chat.id, f"Enter Buying rate for {get_currency_name(currency_id)}:")
        bot.register_next_step_handler(message, get_buying_rate, currency_id)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid input. Please enter a valid amount for the selling rate.")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ An error occurred while processing your request.")

def get_buying_rate(message, currency_id):
    try:
        buying_rate = round(float(message.text), 2)
        user_rates[currency_id]["buying_rate"] = buying_rate

        # Update the data dictionary with the new rates
        for entry in data:
            if entry['id'] == currency_id:
                entry['selling'] = "{:.2f}".format(user_rates[currency_id]["selling_rate"])
                entry['buying'] = "{:.2f}".format(buying_rate)
                break

        # Save the updated data back to the JSON file
        with open('/var/www/html/data.json', 'w') as json_file:
            json.dump(data, json_file, indent=4)

        bot.send_message(
            message.chat.id,
            f"===================\n{get_currency_name(currency_id)} Rates Updated:✅\n===================\nSelling Rate: {user_rates[currency_id]['selling_rate']:.2f} LKR\n===================\nBuying Rate: {buying_rate:.2f} LKR\n==================="
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid input. Please enter a valid amount for the buying rate.")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ An error occurred while processing your request.")

def get_currency_name(currency_id):
    # Helper function to get the currency name based on its ID
    for entry in data:
        if entry['id'] == currency_id:
            return entry['currency_name']

def generate_rates_message():
    rates_message = "Current Currency Rates:\n\n"
    for entry in data:
        currency_name = entry['currency_name']
        selling_rate = float(entry['selling'])
        buying_rate = float(entry['buying'])
        rates_message += f"{currency_name}:📈\nSelling Rate: {selling_rate:.2f} LKR\nBuying Rate: {buying_rate:.2f} LKR\n===================\n"
    return rates_message

# Command handler for /rates
@bot.message_handler(commands=['rates'])
def handle_rates(message):
    try:
        rates_message = generate_rates_message()
        bot.send_message(message.chat.id, rates_message)
    except Exception as e:
        bot.send_message(message.chat.id, "❌ An error occurred while fetching currency rates.")

@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        if message.chat.username not in admins:
            handle_rates(message)
        else:
            bot.send_message(message.chat.id, "Please select an option below:", reply_markup=start_keyboard)
    except Exception as e:
        bot.send_message(message.chat.id, "❌ An error occurred while processing your request.")

def get_post_filenames():
    posts_folder_path = 'posts/'
    post_filenames = [f for f in os.listdir(posts_folder_path) if os.path.isfile(os.path.join(posts_folder_path, f))]
    return post_filenames

# Add a new message handler to handle "Add Admin" and "Remove Admin" options
@bot.callback_query_handler(func=lambda call: call.data in ["add_admin", "remove_admin", "view_admins", "add_post"])
def handle_admin_options(call):
    try:
        print("Handling admin option:", call.data)
        if call.message.chat.username in admins:
            if call.data == "add_admin":
                print("Add admin option selected.")
                bot.send_message(call.message.chat.id, "Please enter the username of the user you want to add as an admin:")
                bot.register_next_step_handler(call.message, add_new_admin)
            elif call.data == "remove_admin":
                print("Remove admin option selected.")
                bot.send_message(call.message.chat.id, "Please enter the username of the user you want to remove as an admin:")
                bot.register_next_step_handler(call.message, remove_admin)
            elif call.data == "view_admins":
                print("View admins option selected.")
                admins_list = "\n".join(admins)
                bot.send_message(call.message.chat.id, f"Current Admins:\n{admins_list}")
            elif call.data == "add_post":
                print("Add post option selected.")
                bot.send_message(call.message.chat.id, "Please send an image to add as a post:")
                bot.register_next_step_handler(call.message, save_image_as_post)
            elif call.data == "remove_post":
                # Get the list of post filenames from the 'posts/' folder
                remove_image_from_posts(call.message)
        else:
            bot.send_message(call.message.chat.id, "❌ An error occurred while processing your request.")
    except Exception as e:
        logging.exception("Error in handle_callback:")
        bot.send_message(call.message.chat.id, "❌ An error occurred while processing your request.")

def save_image_as_post(message):
    try:
        if message.photo:
            # Get the photo ID of the image sent by the user
            photo_id = message.photo[-1].file_id

            # Use the photo ID to download the image
            photo_file = bot.get_file(photo_id)
            downloaded_file = bot.download_file(photo_file.file_path)

            # Save the downloaded image in the posts folder
            posts_folder_path = 'posts/'
            file_name = f"post_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            with open(posts_folder_path + file_name, 'wb') as new_file:
                new_file.write(downloaded_file)

            bot.send_message(message.chat.id, "Image has been saved as a post.")
        else:
            bot.send_message(message.chat.id, "❌ No image was sent. Please send an image to add as a post.")
    except Exception as e:
        print("Error:", e)
        bot.send_message(message.chat.id, "❌ An error occurred while processing your request.")

def remove_image_from_posts(message, post_filenames=None):
    try:
        # If post_filenames is None, retrieve the list of post filenames from the 'posts/' folder
        if post_filenames is None:
            post_filenames = get_post_filenames()

        if not post_filenames:
            bot.send_message(message.chat.id, "No posts available to remove.")
            return

        if message.text.strip().lower() == "/cancel":
            bot.send_message(message.chat.id, "Post removal canceled.")
            return

        # If the user has not entered a filename yet, send the list of file names for selection
        if not message.text:
            file_names_list = "\n".join(post_filenames)
            bot.send_message(message.chat.id, f"Please enter the filename of the image you want to remove:\n{file_names_list}")
            return

        file_name = message.text.strip()
        if file_name not in post_filenames:
            bot.send_message(message.chat.id, f"Image '{file_name}' not found in posts folder.")
            return

        file_path = os.path.join('posts/', file_name)

        if os.path.exists(file_path):
            os.remove(file_path)
            bot.send_message(message.chat.id, f"Image '{file_name}' has been removed from posts.")
            # Check if there are any remaining posts to remove
            if post_filenames:
                next_file_name = post_filenames.pop(0)
                if next_file_name:
                    bot.send_message(message.chat.id, f"Please enter the filename of the next image you want to remove or type '/cancel' to stop:\n{next_file_name}")
                    # Pass the remaining 'post_filenames' list as the second argument
                    bot.register_next_step_handler(message, remove_image_from_posts, post_filenames)
                else:
                    bot.send_message(message.chat.id, "All posts have been removed.")
            else:
                bot.send_message(message.chat.id, "All posts have been removed.")
        else:
            bot.send_message(message.chat.id, f"Image '{file_name}' not found in posts folder.")
    except Exception as e:
        logging.exception("Error in remove_image_from_posts:")
        bot.send_message(message.chat.id, "❌ An error occurred while processing your request.")

def list_posts(message):
    try:
        post_filenames = get_post_filenames()
        if post_filenames:
            posts_list = "\n".join(post_filenames)
            bot.send_message(message.chat.id, f"Current posts in the folder:\n{posts_list}")
        else:
            bot.send_message(message.chat.id, "No posts available.")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ An error occurred while processing your request.")

@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def handle_group_message(message):
    try:
        # Print the group message content to the console
        print(f"Group Message from {message.chat.title} [{message.chat.id}]: {message.text}")
    except Exception as e:
        print(f"❌ An error occurred while processing the group message: {e}")

def add_new_admin_from_callback(message):
    try:
        new_admin_username = message.text.strip()
        if new_admin_username not in admins:
            admins.append(new_admin_username)
            with open('admins.json', 'w') as json_file:
                json.dump({'admins': admins}, json_file)
            bot.send_message(message.chat.id, f"{new_admin_username} has been added as an admin.")

        else:
            bot.send_message(message.chat.id, f"{new_admin_username} is already an admin.")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ An error occurred while processing your request.")

@bot.callback_query_handler(func=lambda call: call.data == "remove_post")
def handle_remove_post(call):
    try:
        # Get the list of post filenames from the 'posts/' folder
        post_filenames = get_post_filenames()

        # Send the list of file names for the user to select
        send_file_names_for_removal(call.message.chat.id, post_filenames)
        
        # Register the next step handler after sending all filenames
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, remove_image_from_posts, post_filenames)
    except Exception as e:
        logging.exception("Error in handle_remove_post:")
        bot.send_message(call.message.chat.id, "❌ An error occurred while processing your request.")

@bot.message_handler(commands=['admin'])
def handle_admin_command(message):
    try:
        if message.chat.username in admins:
            admin_keyboard = telebot.types.InlineKeyboardMarkup()
            admin_keyboard.row(telebot.types.InlineKeyboardButton("Add Admin", callback_data="add_admin"))
            admin_keyboard.row(telebot.types.InlineKeyboardButton("Remove Admin", callback_data="remove_admin"))
            admin_keyboard.row(telebot.types.InlineKeyboardButton("View Admins", callback_data="view_admins"))
            admin_keyboard.row(telebot.types.InlineKeyboardButton("Add Post", callback_data="add_post"))
            admin_keyboard.row(telebot.types.InlineKeyboardButton("Remove Post", callback_data="remove_post"))  # Add the "Remove Post" button
            bot.send_message(message.chat.id, "Please select an option below:", reply_markup=admin_keyboard)
        else:
            bot.send_message(message.chat.id, "You don't have permission to access this command.")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ An error occurred while processing your request.")

def exit_gracefully(signum, frame):
    print("\nBot terminated by user (Ctrl+C).")
    sys.exit(0)

def remove_admin_from_callback(message):
    try:
        username_to_remove = message.text.strip()
        if username_to_remove in admins:
            admins.remove(username_to_remove)
            with open('admins.json', 'w') as json_file:
                json.dump({'admins': admins}, json_file)
            bot.send_message(message.chat.id, f"{username_to_remove} has been removed as an admin.")
        else:
            bot.send_message(message.chat.id, f"{username_to_remove} is not an admin.")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ An error occurred while processing your request.")

@bot.callback_query_handler(func=lambda call: call.data == "remove_admin")
def handle_remove_admin(call):
    try:
        bot.send_message(call.message.chat.id, "Please enter the username of the user you want to remove as an admin:")
        bot.register_next_step_handler(call.message, remove_admin_from_callback)
    except Exception as e:
        logging.exception("Error in handle_callback:")
        bot.send_message(call.message.chat.id, "❌ An error occurred while processing your request.")


def clear_console():
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For Unix/Linux/Mac
    else:
        os.system('clear')

def run_bot():
    # Define the initial delay for backoff (in seconds)
    backoff_delay = 5

    # Register the exit_gracefully function to handle SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, exit_gracefully)

    try:
        while True:
            try:
                bot.polling()
            except Exception as e:
                timestamp = get_timestamp()
                # Log the error for debugging and monitoring purposes
                print(f"{timestamp} - An unexpected error occurred:", e)

                # Implement a backoff strategy with a delay before retrying
                print(f"{timestamp} - Retrying after {backoff_delay} seconds...")
                time.sleep(backoff_delay)

                # Double the backoff delay for the next retry (up to a maximum of 60 seconds)
                backoff_delay = min(backoff_delay * 2, 60)

    except KeyboardInterrupt:
        print("\nBot terminated by user (Ctrl+C).")
        sys.exit(0)

def get_chat_id_from_json(file_path, group_name):
    with open(file_path, 'r') as json_file:
        groups_data = json.load(json_file)
        for group in groups_data['groups']:
            if group['group_name'] == group_name:
                return group['chat_id']
    return None

def send_image_periodically():
    groups_file_path = 'groups.json'  # Replace this with the actual path of your groups.json file
    images_folder_path = 'posts/'  # Replace this with the path of the folder containing your images
    caption = "Test Caption"  # Replace this with the desired caption for the image

    with open(groups_file_path, 'r') as json_file:
        groups_data = json.load(json_file)

    # Get a list of all image filenames in the images folder
    image_files = [f for f in os.listdir(images_folder_path) if os.path.isfile(os.path.join(images_folder_path, f))]

    # Shuffle the list of image files for random selection
    random.shuffle(image_files)

    while True:
        for group in groups_data["groups"]:
            chat_id = group.get("chat_id")
            group_name = group.get("name")

            if chat_id is not None and image_files:
                try:
                    # Pop the first image from the list for sending
                    image_file = image_files.pop(0)

                    # Construct the full path of the image
                    image_path = os.path.join(images_folder_path, image_file)

                    # Send the image to the group with the specified caption
                    with open(image_path, 'rb') as photo:
                        bot.send_photo(chat_id, photo, caption=caption)

                except Exception as e:
                    print(f"An error occurred while sending the image to group '{group_name}': {e}")
            
        if not image_files:
            # If all images have been sent, shuffle the list again for the next round
            image_files = [f for f in os.listdir(images_folder_path) if os.path.isfile(os.path.join(images_folder_path, f))]
            random.shuffle(image_files)

        # Wait for 5 seconds before sending the next image to all groups
        time.sleep(18000)

def get_timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

clear_console()
timestamp = get_timestamp()   
art = r'''
__________         __                     .__   ____  __.
\______   \_____ _/  |_  ____   ______    |  | |    |/ _|
 |       _/\__  \\   __\/ __ \ /  ___/    |  | |      <  
 |    |   \ / __ \|  | \  ___/ \___ \     |  |_|    |  \ 
 |____|_  /(____  /__|  \___  >____  > /\ |____/____|__ \
        \/      \/          \/     \/  \/              \/
                                            
                                       V1.0    © @akilaid
'''

print(art)
print(f"       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n            - Developed by Akila Indunil - \n        - Github : https://github.com/akilaid - \n       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n")
print(f"===============================================\n{timestamp} - Bot started successfully!\n===============================================\n\nTerminate using (Ctrl+C).")

if __name__ == "__main__":
    # Create a new thread to run the image-sending function
    image_thread = threading.Thread(target=send_image_periodically)
    image_thread.daemon = True
    image_thread.start()

    run_bot()
