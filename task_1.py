from functools import wraps
from collections import UserDict
from datetime import datetime, timedelta
from typing import Callable, Any


def input_error(func: Callable) -> Callable:
    @wraps(func)
    def inner(*args, **kwargs) -> str:
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            # Catches data validation errors
            # (incorrect phone number, date)
            # And errors due to missing arguments,
            # which we will discard manually
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

    def __init__(self, value: Any) -> None:
        self.value = value

    def __str__(self) -> str:
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

    def __init__(self, value: str) -> None:
        if len(value) != 10:
            raise ValueError("Phone number must be a 10-digit number.")
        super().__init__(value)


class Birthday(Field):
    def __init__(self, value: str) -> None:
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

    def __init__(self, name: str) -> None:
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone: str) -> None:
        if self.find_phone(phone):
            raise ValueError("Phone already exists")

        self.phones.append(Phone(phone))

    def remove_phone(self, phone: str) -> None:
        is_phone = self.find_phone(phone)
        if is_phone is None:
            raise ValueError(f"Phone {phone} not found in this contact.")
        self.phones.remove(is_phone)

    def edit_phone(self, old_phone: str, new_phone: str) -> None:
        is_phone = self.find_phone(old_phone)
        if is_phone is None:
            raise ValueError(f"Phone {old_phone} not found in this contact.")

        Phone(new_phone)  # Validate new phone first to avoid partial update

        self.remove_phone(old_phone)
        self.add_phone(new_phone)

    def find_phone(self, phone: str) -> Phone | None:
        for p in self.phones:
            if p.value == phone:
                return p
        return None

    def add_birthday(self, birthday: str) -> None:
        correct_birthday = Birthday(birthday)
        self.birthday = correct_birthday


#    def __str__(self):
#        return f"Contact name: {self.name.value}, phones: {'; '.join(p.value for p in self.phones)}."


class AddressBook(UserDict):
    """
    Container for contact records.
    """

    def add_record(self, record: Record) -> None:
        self.data[record.name.value] = record

    def find(self, name: str) -> Record | None:
        return self.data.get(name)

    def delete(self, name: str) -> None:
        if name in self.data:
            del self.data[name]
        else:
            raise KeyError(f"Contact '{name}' not found.")


def parse_input(user_input: str) -> tuple:
    """
    Parses the user input into a command and arguments.
    """
    cmd, *args = user_input.split()
    cmd = cmd.strip().lower()
    return cmd, *args


@input_error
def add_contact(args, book: AddressBook) -> str:
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
def change_contact_phone(args, book: AddressBook) -> str:
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
def show_phone(args, book: AddressBook) -> str:
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
def add_birthday(args, book: AddressBook) -> str:
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
def show_birthday(args, book: AddressBook) -> str:
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
    return str(record.birthday) if record.birthday else "Birthday not set."


def birthdays(book: AddressBook) -> str:
    today = datetime.today().date()
    upcoming = []

    for name, record in book.data.items():
        if not record.birthday:
            continue

        # We determine the date of birth this year to check if it's upcoming
        bday = record.birthday.value.replace(year=today.year)
        if bday < today:
            bday = bday.replace(year=today.year + 1)

        # Elegant table formatting with weekend handling
        if 0 <= (bday - today).days <= 7:
            # Transfer from the weekend to Monday
            weekday = bday.weekday()
            congr_date = bday + timedelta(
                days=(7 - weekday if weekday >= 5 else 0)
            )

            upcoming.append(
                {"name": name, "date": congr_date.strftime("%d-%m-%Y")}
            )

    if not upcoming:
        return "No upcoming birthdays in the next 7 days."

    # Elegant table formatting
    header = f"{'Name':<15} | {'Congratulation Date':<20}"
    separator = "-" * 45

    lines = [separator, header, separator]

    for item in upcoming:
        lines.append(f"{item['name']:<15} | {item['date']:<20}")
        lines.append(separator)

    return "\n".join(lines)


def show_all(book: AddressBook) -> str:
    """
    Displays all saved contacts.
    Usage: all
    """
    if not book.data:
        return "Address book is empty."

    header = f"{'Name':<21} | {'Phone':<21}"
    separator = "-" * 45

    lines = [separator, header, separator]

    for record in book.data.values():
        phones = record.phones
        first_phone = phones[0].value if phones else "No phones"
        lines.append(f"{record.name.value:<21} | {first_phone:<21}")

        if len(phones) > 1:
            for phone in phones[1:]:
                lines.append(f'{"":<21} | {phone.value:<21}')
        lines.append(separator)

    return "\n".join(lines)


def main() -> None:
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
