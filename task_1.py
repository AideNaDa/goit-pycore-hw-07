from functools import wraps
from collections import UserDict
from datetime import datetime, timedelta


def input_error(func):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            # Catches data validation errors (incorrect phone number, date)
            # And errors due to missing arguments, which we will discard manually
            return str(e)
        except KeyError as e:
            # Catches "Contact not found" errors
            return str(e).strip("'")
        except IndexError:
            # In case len(args) was missed somewhere
            return "Enter user name."
        except Exception as e:
            # Any other unforeseen error
            return f"An unexpected error occurred: {e}"

    return inner


class Field:
    """
    Base class for contact fields.
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    """
    Contact name.
    """

    pass


class Phone(Field):
    """
    Phone number with basic validation.
    """

    def __init__(self, value):
        if len(value) != 10:
            raise ValueError("Phone number must be a 10-digit number.")
        super().__init__(value)


class Birthday(Field):
    def __init__(self, value):
        try:
            date_obj = datetime.strptime(value, "%d-%m-%Y").date()
        except ValueError:
            if "-" not in value:
                raise ValueError("Invalid date format. Use DD-MM-YYYY")
            raise ValueError(f"Invalid date: '{value}' does not exist.")

        super().__init__(date_obj)


class Record:
    """
    Single contact record.
    """

    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone):
        if self.find_phone(phone):
            raise ValueError("Phone already exists")

        self.phones.append(Phone(phone))

    def remove_phone(self, phone):
        is_phone = self.find_phone(phone)
        if is_phone is None:
            raise ValueError(f"Phone {phone} not found in this contact.")
        self.phones.remove(is_phone)

    def edit_phone(self, old_phone, new_phone):
        is_phone = self.find_phone(old_phone)
        if is_phone is None:
            raise ValueError(f"Phone {old_phone} not found in this contact.")

        Phone(new_phone)  # Validate new phone first to avoid partial update

        self.remove_phone(old_phone)
        self.add_phone(new_phone)

    def find_phone(self, phone):
        for p in self.phones:
            if p.value == phone:
                return p
        return None

    def add_birthday(self, birthday):
        correct_birthday = Birthday(birthday)
        self.birthday = correct_birthday


#    def __str__(self):
#        return f"Contact name: {self.name.value}, phones: {'; '.join(p.value for p in self.phones)}."


class AddressBook(UserDict):
    """
    Container for contact records.
    """

    def add_record(self, record):
        self.data[record.name.value] = record

    def find(self, name):
        return self.data.get(name)

    def delete(self, name):
        if name in self.data:
            del self.data[name]
        else:
            raise KeyError(f"Contact '{name}' not found.")

    def get_upcoming_birthdays(self):
        """
        Finds birthdays within 7 days and carries over congratulations from weeks
        """
        current_date = datetime.today().date()
        congr_date_list = []

        for user in self.data:
            # convert srting to object date
            record = self.data[user]

            if record.birthday is None:
                continue

            birthday_date = record.birthday.value
            birthday_this_year = birthday_date.replace(year=current_date.year)

            # if birthday has already passed this year try next year
            if birthday_this_year < current_date:
                birthday_this_year = birthday_date.replace(year=current_date.year + 1)

            difference_days = (birthday_this_year - current_date).days

            # check if the date falls within the 7-day interval
            if 0 <= difference_days <= 7:

                congr_date = birthday_this_year
                # transfer from weekend to Monday
                # 6 - Sunday, 5 - Saturday
                match birthday_this_year.weekday():
                    case 6:
                        congr_date += timedelta(days=1)
                    case 5:
                        congr_date += timedelta(days=2)

                congr_date_list.append(
                    {
                        "name": user,
                        "congratulation_date": congr_date.strftime("%d-%m-%Y"),
                    }
                )

        return congr_date_list


def parse_input(user_input):
    """
    Parses the user input into a command and arguments.
    """
    cmd, *args = user_input.split()
    cmd = cmd.strip().lower()
    return cmd, *args


@input_error
def add_contact(args, book):
    """
    Add either a new contact with a name and phone number,
    or a phone number to an existing contact.
    Usage: add [name] [phone]
    """
    if len(args) < 2:
        raise ValueError("Usage: add [name] [phone]")

    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    Phone(phone)  # Validate new phone first to avoid partial update
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message


@input_error
def change_contact_phone(args, book):
    """
    Updates the phone number for an specified existing contact.
    Usage: change [name] [old_phone] [new_phone]
    """
    if len(args) < 3:
        raise ValueError("Usage: change [name] [old_phone] [new_phone]")
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError(f"Contact '{name}' not found.")
    record.edit_phone(old_phone, new_phone)
    return "Contact phone number updated."


@input_error
def show_phone(args, book):
    """
    Shows the phone number for a specific contact.
    Usage: phone [name]
    """
    if len(args) < 1:
        raise ValueError("Usage: phone [name]")

    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError(f"Contact '{name}' not found.")
    return f"phones: {'; '.join(p.value for p in record.phones)}."


@input_error
def add_birthday(args, book):
    """
    Add a date of birth for the specified contact.
    Usage: add-birthday [name] [birthday date]
    """
    message = "Contact's birthday added"
    if len(args) < 2:
        raise ValueError("Usage: add-birthday [name] [birthday date]")
    name, birthday_date, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError(f"Contact '{name}' not found.")
    if record.birthday:
        message = "Contact's birthday updated"
    record.add_birthday(birthday_date)
    return message


@input_error
def show_birthday(args, book):
    """
    Display the date of birth for the specified contact.
    Usage: show-birthday [name]
    """
    if len(args) < 1:
        raise ValueError("Usage: show-birthday [name]")
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError(f"Contact '{name}' not found.")
    return record.birthday


def birthdays(book):
    """
    Show birthdays that will occur during the next 7 days.
    Usage: birthdays
    """
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No upcoming birthdays in the next 7 days."

    header = f"{'Name':<15} | {'Upcoming birthdays':<20}"
    separator = "-" * len(header)

    lines = [header, separator]

    for record in upcoming:
        lines.append(f"{record['name']:<15} | {record['congratulation_date']:<20}")
        lines.append(separator)

    return "\n".join(lines)


def show_all(book):
    """
    Displays all saved contacts.
    Usage: all
    """
    if not book.data:
        return "Address book is empty."

    header = f"{'Name':<15} | {'Phone':<15}"
    separator = "-" * len(header)

    lines = [header, separator]

    for record in book.data.values():
        phones = record.phones
        first_phone = phones[0].value if phones else "No phones"
        lines.append(f"{record.name.value:<15} | {first_phone:<15}")

        if len(phones) > 1:
            for phone in phones[1:]:
                lines.append(f'{"":<15} | {phone.value:<15}')
        lines.append(separator)

    return "\n".join(lines)


def main():
    """
    Main loop for the assistant bot.
    """
    book = AddressBook()
    print("Welcome to the assistant bot!")
    while True:
        try:
            user_input = input("Enter a command: ")
            if not user_input.strip():
                continue
        except KeyboardInterrupt:
            print("\nGood bye!")
            break
        command, *args = parse_input(user_input)

        if command in ["close", "exit"]:
            print("Good bye!")
            break
        elif command == "hello":
            print("How can I help you?")
        elif command == "add":
            print(add_contact(args, book))
        elif command == "change":
            print(change_contact_phone(args, book))
        elif command == "phone":
            print(show_phone(args, book))
        elif command == "all":
            print(show_all(book))
        elif command == "add-birthday":
            print(add_birthday(args, book))
        elif command == "show-birthday":
            print(show_birthday(args, book))
        elif command == "birthdays":
            print(birthdays(book))
        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()
