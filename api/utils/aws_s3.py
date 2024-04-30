import boto3
from dotenv import load_dotenv
import os
import io

from PIL import Image

load_dotenv()

s3 = boto3.client(
    's3',
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
)

allowed_file_extensions = ['png', 'jpg', 'jpeg', 'gif']
max_file_size_bytes = 10 * 1024 * 1024


def compress_and_resize_image (file) :
    try :
        image = Image.open(io.BytesIO(file))

        # for png file uploads
        if image.mode == 'RGBA' :
            image = image.convert('RGB')
        resized_image = image.resize((250, 250))

        output = io.BytesIO()
        resized_image.save(output, format ='JPEG')

        output.seek(0)

        return output

    except Exception as error :
        raise ValueError(f'Error compressing and resizing image: {str(error)}')

def s3_photo_upload (file, product_id) :
    file_type = file.filename.split('.')[-1].lower()

    if file_type not in allowed_file_extensions :
        raise ValueError('Invalid file type')
    
    file_name = f'{product_id}.{file_type}'

    resized_file = compress_and_resize_image(file.read())

    if resized_file :
        try :
            s3.upload_fileobj(
                resized_file,
                os.getenv('S3_BUCKET_NAME'),
                file_name,
            )

            return 'https://{}.s3.amazonaws.com/{}'.format(os.getenv('S3_BUCKET_NAME'), file_name)

        except Exception as error :
            raise ValueError(f'Error uploading image to S3: {str(error)}')
    else :
        return None