import boto3
from dotenv import load_dotenv
import os
import io

from PIL import Image

load_dotenv()

# initialize s3 client with credients from env vars
s3 = boto3.client(
    's3',
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
)

# defines allowed file extensions for image uploads and maximum file sizes in bytes
allowed_file_extensions = ['png', 'jpg', 'jpeg', 'gif']
max_file_size_bytes = 10 * 1024 * 1024


def compress_and_resize_image (file) :
    '''
    Compresses and resizes an image to 250 x 250 pixels, while converting to JPEG format.
    If image is a PNG with alpha channel, it is converted to RGB.

    Args :
        file (bytes) : image file to be processed.

    Returns :
        BytesIO : processed image as an in-memory byte stream.
    
        
    Raises :
        ValueError : if there is an error during image processing.
    '''
    try :
        
        image = Image.open(io.BytesIO(file))

        # for png file uploads, convert to RGB
        if image.mode == 'RGBA' :
            image = image.convert('RGB')

        resized_image = image.resize((250, 250))

        # create in-memory byte stream to save processed image
        output = io.BytesIO()
        resized_image.save(output, format ='JPEG')

        # reset stream position to start
        output.seek(0)

        return output

    except Exception as error :
        raise ValueError(f'Error compressing and resizing image: {str(error)}')


def s3_photo_upload (file, product_id) :
    '''
    Uploads a photo to S# bucket.

    Checks file extension, uses compress and resize helper, then uploads to S3 bucket
    under name based on product ID.

    Args :
        file (FileStorage) : the image file to be uploaded.
        product_id (str) : ID of product to associate with uploaded image.

    Returns :
        str : the URL of the uploaded image in S3 bucket

    Raises :
        ValueError : if the file type is invalid or if there is an error during upload.
    '''

    # extract file extension and check if allowed
    file_type = file.filename.split('.')[-1].lower()

    if file_type not in allowed_file_extensions :
        raise ValueError('Invalid file type')
    
    # generate file name based on product ID
    file_name = f'products/{product_id}.{file_type}'

    # compress and resize image
    resized_file = compress_and_resize_image(file.read())

    if resized_file :
        try :
            # upload processed image to S3 bucket
            s3.upload_fileobj(
                resized_file,
                os.getenv('S3_BUCKET_NAME'),
                file_name,
            )

            # return image's S3 bucket URL
            return 'https://{}.s3.amazonaws.com/{}'.format(os.getenv('S3_BUCKET_NAME'), file_name)

        except Exception as error :
            raise ValueError(f'Error uploading image to S3: {str(error)}')
    else :
        return None